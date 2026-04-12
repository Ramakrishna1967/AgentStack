# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
import signal
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple

from redis.asyncio import Redis
import msgpack

logger = logging.getLogger(__name__)

class BaseConsumer(ABC):
    """Base class for Redis Stream consumers."""

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
                raise  # HIGH-6 FIX: fail fast — don't run a broken worker

        # Setup signal handlers (graceful shutdown)
        # Note: In some environments (like Windows), signals might need different handling or run via uvicorn's lifespan
        # For now, we rely on the `stop` method being called or external cancellation.

        logger.info(f"Starting consumer {self.consumer_name} on {self.stream_key}")
        
        while self.running:
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
                        except Exception as process_e:
                            logger.error("Failed to process message %s: %s", message_id, process_e, exc_info=True)
                            # Dead Letter Queue implementation
                            try:
                                dlq_stream = f"{self.stream_key}:dlq"
                                await self.redis.xadd(dlq_stream, data)
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
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(1.0)
        
        await self.cleanup()

    async def stop(self):
        """Graceful shutdown trigger."""
        logger.info("Stopping consumer...")
        self.running = False
        self._shutdown_event.set()

    async def cleanup(self):
        """Cleanup resources."""
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
        """Helper to decode msgpack data."""
        return msgpack.unpackb(data, raw=False)
