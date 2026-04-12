# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
import time
import json
import uuid
from typing import List, Dict, Any

from clickhouse_connect import get_client
from clickhouse_connect.driver.client import Client as ClickHouseClient

from workers.consumer import BaseConsumer

logger = logging.getLogger(__name__)

class ClickHouseWriter(BaseConsumer):
    """Worker that reads spans from Redis and writes to ClickHouse."""

    def __init__(
        self,
        redis_url: str,
        clickhouse_host: str = "localhost",
        clickhouse_port: int = 8123,
        clickhouse_user: str = "default",
        clickhouse_password: str = "",
        batch_size: int = 1000,
        flush_interval: float = 1.0,
    ):
        super().__init__(
            redis_url=redis_url,
            stream_key="spans.ingest",
            group_name="writer-group",
            consumer_name=f"worker-writer-{uuid.uuid4().hex[:8]}",
            batch_size=batch_size,
        )
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.clickhouse_user = clickhouse_user
        self.clickhouse_password = clickhouse_password
        self.flush_interval = flush_interval
        self.buffer: List[tuple] = []  # List of (message_id, data_dict)
        self.last_flush = time.time()
        self.ch_client: ClickHouseClient | None = None
        
        # Ensure logs are not buffered
        import sys
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, line_buffering=True)

    async def start(self):
        """Override start to initialize ClickHouse client and use custom loop without auto-ACK."""
        logger.info(f"Connecting to ClickHouse at {self.clickhouse_host}:{self.clickhouse_port}...")
        try:
            self.ch_client = get_client(
                host=self.clickhouse_host, 
                port=self.clickhouse_port,
                username=self.clickhouse_user,
                password=self.clickhouse_password
            )
            logger.info("Successfully connected to ClickHouse")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

        # Connect to Redis directly
        from redis.asyncio import Redis
        logger.info(f"Connecting to Redis at {self.redis_url}...")
        self.redis = Redis.from_url(self.redis_url, decode_responses=False)
        self.running = True

        # Ensure consumer group exists
        try:
            await self.redis.xgroup_create(
                self.stream_key, self.group_name, id="$", mkstream=True
            )
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Error creating group: {e}")

        logger.info(f"--- CLICKHOUSE WRITER STARTING CONSUMPTION ---")
        logger.info(f"Stream: {self.stream_key}, Group: {self.group_name}")

        while self.running:
            try:
                # Read from Redis (blocking)
                streams = await self.redis.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_key: ">"},
                    count=self.batch_size,
                    block=1000, # 1s wait
                )

                if streams:
                    for _, messages in streams:
                        for message_id, data in messages:
                            await self.process_message(message_id, data)
                
                # Always check flush interval
                if (time.time() - self.last_flush) >= self.flush_interval:
                    await self.flush_buffer()

            except asyncio.CancelledError:
                logger.info("ClickHouseWriter loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in ClickHouseWriter loop: {e}", exc_info=True)
                await asyncio.sleep(2.0) # Back off on error

        # Final flush on shutdown
        await self.flush_buffer()
        await self.cleanup()


    async def process_message(self, message_id: bytes, data: Dict[bytes, bytes]):
        """Accumulate messages in buffer."""
        try:
            # Decode MsgPack
            if b"data" in data:
                payload = self.decode_msgpack(data[b"data"])
                self.buffer.append((message_id, payload))
            else:
                logger.warning(f"Skipping malformed message {message_id}: missing 'data' field")
                # We still ack validly formatted but empty messages to move past them?
                # Actually, better to let them be acked in the batch.
        except Exception as e:
            logger.error(f"Error decoding message {message_id}: {e}")

        # Check flush conditions
        if len(self.buffer) >= self.batch_size or (time.time() - self.last_flush) >= self.flush_interval:
            await self.flush_buffer()

    async def flush_buffer(self):
        """Flush buffer to ClickHouse."""
        if not self.buffer:
            self.last_flush = time.time()
            return

        spans_to_insert = []
        message_ids = []

        # Transform data for ClickHouse Schema
        # Schema: span_id, trace_id, parent_span_id, project_id, name, service_name, status, start_time, end_time, duration_ms, attributes, events
        for msg_id, span in self.buffer:
            message_ids.append(msg_id)
            
            # Helper to safely get fields
            spans_to_insert.append([
                span.get("span_id"),
                span.get("trace_id"),
                span.get("parent_span_id") or "",
                span.get("project_id"),
                span.get("name"),
                span.get("service_name", "unknown"),
                span.get("status", "UNSET"),
                span.get("start_time"), # DateTime64 expects int/float timestamp? clickhouse-connect handles python datetime or int
                span.get("end_time"),
                span.get("duration_ms"),
                span.get("attributes", {}), # Map(String, String)
                json.dumps(span.get("events", [])), # String (JSON)
            ])

        if not spans_to_insert:
            self.buffer = []
            return

        try:
            # Execute Batch Insert
            # We use a loop/executor to run sync CH client in async context
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._insert_sync, spans_to_insert)
            
            # ACK all messages using pipeline
            pipeline = self.redis.pipeline()
            for msg_id in message_ids:
                pipeline.xack(self.stream_key, self.group_name, msg_id)
            await pipeline.execute()

            logger.info(f"Flushed {len(spans_to_insert)} spans to ClickHouse")
            
        except Exception as e:
            logger.error(f"Failed to flush batch to ClickHouse: {e}")
            # Infinite retry logic is implicit: we don't clear buffer, next loop will retry?
            # Actually, if we fail here, we should probably throw or sleep so we don't ACK.
            # Base consumer loop catches and sleeps.
            # But we must NOT clear self.buffer if we want to retry.
            # Re-raising exception will trigger the BaseConsumer's error handler (sleep 1s) and retry.
            raise

        # Clear buffer on success
        self.buffer = []
        self.last_flush = time.time()

    def _insert_sync(self, data):
        """Sync wrapper for clickhouse insert."""
        self.ch_client.insert(
            "spans",
            data,
            column_names=[
                "span_id", "trace_id", "parent_span_id", "project_id", "name", 
                "service_name", "status", "start_time", "end_time", "duration_ms", 
                "attributes", "events"
            ]
        )

if __name__ == "__main__":
    # Entry point
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ch_host = os.getenv("CLICKHOUSE_HOST", "localhost")
    ch_user = os.getenv("CLICKHOUSE_USER", "default")
    ch_pass = os.getenv("CLICKHOUSE_PASSWORD", "")
    
    worker = ClickHouseWriter(
        redis_url=redis_url, 
        clickhouse_host=ch_host,
        clickhouse_user=ch_user,
        clickhouse_password=ch_pass
    )
    asyncio.run(worker.start())
