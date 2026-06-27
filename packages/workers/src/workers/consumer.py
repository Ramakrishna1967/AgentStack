# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
import signal
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple

from redis.asyncio import Redis
import msgpack

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker to prevent infinite retry loops on persistent failures."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = "closed"  # closed, open, half_open
        self.half_open_attempts = 0

    def record_success(self) -> None:
        """Record a successful operation."""
        self.failure_count = 0
        self.state = "closed"
        self.half_open_attempts = 0

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures. "
                f"Will retry after {self.recovery_timeout}s."
            )

    def can_execute(self) -> bool:
        """Check if an operation can be executed."""
        if self.state == "closed":
            return True
        if self.state == "open":
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half_open"
                self.half_open_attempts = 0
                logger.info("Circuit breaker entering HALF_OPEN state")
                return True
            return False
        if self.state == "half_open":
            return self.half_open_attempts < self.half_open_max
        return False


class BaseConsumer(ABC):
    """Base class for Redis Stream consumers with circuit breaker support."""

    def __init__(
        self,
        redis_url: str,
        stream_key: str,
        group_name: str,
        consumer_name: str,
        batch_size: int = 10,
        poll_interval: float = 0.1,
        auto_ack: bool = True,
    ):
        self.redis_url = redis_url
        self.stream_key = stream_key
        self.group_name = group_name
        self.consumer_name = consumer_name
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.auto_ack = auto_ack
        
        self.redis: Optional[Redis] = None
        self.running = False
        self._shutdown_event = asyncio.Event()
        self.circuit_breaker = CircuitBreaker()
        
        # Metrics
        self._messages_processed = 0
        self._messages_failed = 0
        self._messages_dlq = 0

    async def start(self):
        """Start the consumer loop."""
        self.redis = Redis.from_url(self.redis_url, decode_responses=False)
        self.running = True
        
        # Ensure consumer group exists
        try:
            await self.redis.xgroup_create(
                self.stream_key, self.group_name, id="$", mkstream=True
            )
            logger.info("Created consumer group %s", self.group_name)
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.info("Consumer group %s already exists", self.group_name)
            else:
                logger.error("Fatal error creating consumer group %s: %s", self.group_name, e)
                raise  # HIGH-6 FIX: fail fast  don't run a broken worker

        # Setup signal handlers (graceful shutdown)
        # Note: In some environments (like Windows), signals might need different handling or run via uvicorn's lifespan
        # For now, we rely on the `stop` method being called or external cancellation.

        logger.info(f"Starting consumer {self.consumer_name} on {self.stream_key}")
        
        while self.running:
            # Circuit breaker: skip processing if open
            if not self.circuit_breaker.can_execute():
                logger.debug("Circuit breaker is OPEN, waiting before retry...")
                await asyncio.sleep(self.circuit_breaker.recovery_timeout)
                continue

            try:
                # Read from stream
                streams = await self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=self.batch_size,
                    block=int(self.poll_interval * 1000),
                )

                if not streams:
                    if hasattr(self, "on_idle"):
                        import inspect
                        if inspect.iscoroutinefunction(self.on_idle):
                            await self.on_idle()
                        else:
                            self.on_idle()
                    continue

                for _, messages in streams:
                    for message_id, data in messages:
                        success = False
                        try:
                            await self.process_message(message_id, data)
                            success = True
                            self._messages_processed += 1
                            self.circuit_breaker.record_success()
                        except Exception as process_e:
                            self._messages_failed += 1
                            self.circuit_breaker.record_failure()
                            logger.error("Failed to process message %s: %s", message_id, process_e, exc_info=True)
                            # Dead Letter Queue implementation
                            try:
                                dlq_stream = f"{self.stream_key}:dlq"
                                await self.redis.xadd(dlq_stream, data)
                                self._messages_dlq += 1
                                logger.info("Message %s routed to DLQ %s", message_id, dlq_stream)
                            except Exception as dlq_e:
                                logger.error("Fatal: Could not write message %s to DLQ: %s", message_id, dlq_e)

                        if self.auto_ack or not success:
                            # Always ACK to remove it from PEL, since it's either successful or in DLQ
                            await self.redis.xack(self.stream_key, self.group_name, message_id)

            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled")
                break
            except Exception as e:
                self.circuit_breaker.record_failure()
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(1.0)
        
        await self.cleanup()

    async def stop(self):
        """Graceful shutdown trigger."""
        logger.info("Stopping consumer...")
        self.running = False
        self._shutdown_event.set()

    async def cleanup(self):
        """Cleanup resources and log final metrics."""
        logger.info(
            f"Consumer {self.consumer_name} shutting down. "
            f"Processed: {self._messages_processed}, "
            f"Failed: {self._messages_failed}, "
            f"DLQ: {self._messages_dlq}"
        )
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

    @abstractmethod
    async def process_message(self, message_id: bytes, data: Dict[bytes, bytes]):
        """Process a single message.
        
        Args:
            message_id: The ID of the message.
            data: The message data (bytes).
        """
        pass

    def decode_msgpack(self, data: bytes) -> Dict[str, Any]:
        """Helper to decode msgpack data with security validation.
        
        SECURITY: Uses strict_map_key to prevent hash collision attacks
        and limits max buffer size to prevent memory exhaustion.
        """
        # SECURITY: Limit max message size (10MB) to prevent memory exhaustion
        MAX_MSGPACK_SIZE = 10 * 1024 * 1024  # 10MB
        if len(data) > MAX_MSGPACK_SIZE:
            raise ValueError(f"Message too large: {len(data)} bytes (max {MAX_MSGPACK_SIZE})")
        
        # SECURITY: strict_map_key=True prevents hash collision attacks
        # raw=False ensures proper string types
        return msgpack.unpackb(
            data, 
            raw=False, 
            strict_map_key=True,
            max_array_len=10000,
            max_map_len=1000,
            max_str_len=10*1024*1024  # 10MB strings
        )
