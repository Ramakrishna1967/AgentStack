# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

import os
import msgpack
import logging
from redis.asyncio import Redis
from collector.config import settings

logger = logging.getLogger(__name__)

class RedisWriter:
    """Async Redis writer for high-throughput span ingestion."""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL if hasattr(settings, 'REDIS_URL') else os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.mock_mode = os.getenv("MOCK_REDIS", "false").lower() == "true"
        self.redis: Redis | None = None
        self.stream_key = "spans.ingest"

    async def connect(self):
        """Establish Redis connection."""
        if self.mock_mode:
            logger.warning("Running RedisWriter in MOCK_REDIS mode. Spans will be dropped!")
            return

        if not self.redis:
            self.redis = Redis.from_url(self.redis_url, decode_responses=False)
            # Test connection
            try:
                await self.redis.ping()
                logger.info("Connected to Redis at %s", self.redis_url.split("@")[-1])
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    async def close(self):
        """Close Redis connection."""
        if self.mock_mode:
            return
            
        if self.redis:
            await self.redis.close()
            self.redis = None

    async def add_span(self, span_data: dict):
        """Add a span to the ingestion stream.
        
        Args:
            span_data: Dictionary containing span fields.
        """
        if self.mock_mode:
            return # Drop payload in mock mode for benchmarking on Windows
            
        if not self.redis:
            await self.connect()
            
        # Serialize with MsgPack for compactness
        packed_data = msgpack.packb(span_data, use_bin_type=True)
        
        # XADD to stream. We use a single field 'data' to store the blob.
        # This keeps the stream entry size small and fixed structure.
        await self.redis.xadd(
            self.stream_key,
            {"data": packed_data},
            maxlen=1000000, # Cap stream at 1M entries to prevent OOM if workers die
            approximate=True
        )

# Global instance
redis_writer = RedisWriter()
