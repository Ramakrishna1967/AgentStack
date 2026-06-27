# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import logging
import time
import json
import uuid
from typing import Dict, Any, List

from clickhouse_connect import get_client
from clickhouse_connect.driver.client import Client as ClickHouseClient

from workers.consumer import BaseConsumer

logger = logging.getLogger(__name__)

# Simple Pricing Catalog (USD per 1K tokens)
# In production, this should be fetched from an API or DB
PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}

class CostCalculator(BaseConsumer):
    """Worker that calculates cost of LLM spans."""

    def __init__(
        self,
        redis_url: str,
        clickhouse_host: str = "localhost",
        clickhouse_port: int = 8123,
        clickhouse_user: str = "default",
        clickhouse_password: str = "",
        batch_size: int = 100,
        flush_interval: float = 5.0, # Less urgent than security alerts
    ):
        super().__init__(
            redis_url=redis_url,
            stream_key="spans.ingest",
            group_name="cost-group",
            consumer_name=f"worker-cost-{uuid.uuid4().hex[:8]}",
            batch_size=batch_size, 
            auto_ack=False,
        )
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.clickhouse_user = clickhouse_user
        self.clickhouse_password = clickhouse_password
        self.ch_client = None
        self.buffer = []
        self.last_flush = time.time()

    async def start(self):
        try:
            self.ch_client = get_client(
                host=self.clickhouse_host, 
                port=self.clickhouse_port,
                username=self.clickhouse_user,
                password=self.clickhouse_password
            )
            logger.info(f"Connected to ClickHouse at {self.clickhouse_host}:{self.clickhouse_port}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise RuntimeError("Fatal: ClickHouse connection required for CostCalculator")
        await super().start()

    async def process_message(self, message_id: bytes, data: Dict[bytes, bytes]):
        try:
            if b"data" not in data:
                return
                
            span = self.decode_msgpack(data[b"data"])
            self.calculate_cost(message_id, span)
            
        except Exception as e:
            logger.error(f"Error processing cost for span {message_id}: {e}")
            raise

        # Check flush conditions
        if len(self.buffer) >= self.batch_size or (time.time() - self.last_flush) >= 1.0:
            await self.flush_buffer()

    async def on_idle(self):
        """Called when no messages are received from Redis."""
        if self.buffer and (time.time() - self.last_flush) >= 1.0:
            await self.flush_buffer()

    def calculate_cost(self, message_id: bytes, span: dict):
        """Extract usage and calculate cost."""
        attrs = span.get("attributes", {})
        
        # Check if span is an LLM call
        # We look for model name or usage stats
        model = attrs.get("llm.model", attrs.get("model", "")).lower()
        if not model:
            return # Skip non-LLM spans
            
        # Extract tokens  support both OpenTelemetry-style (llm.usage.*) and SDK-style (llm.tokens.*)
        prompt_tokens = int(attrs.get("llm.usage.prompt_tokens", attrs.get("llm.tokens.in", 0)))
        completion_tokens = int(attrs.get("llm.usage.completion_tokens", attrs.get("llm.tokens.out", 0)))
        total_tokens = int(attrs.get("llm.usage.total_tokens", prompt_tokens + completion_tokens))
        
        if total_tokens == 0:
            return
            
        # Find price
        # Normalize model name (e.g. gpt-4-0613 -> gpt-4)
        price_info = None
        for key in PRICING:
            if key in model:
                price_info = PRICING[key]
                break
                
        if not price_info:
            logger.debug(f"Unknown model for pricing: {model}")
            return
            
        # Calculate Cost
        input_cost = (prompt_tokens / 1000) * price_info["input"]
        output_cost = (completion_tokens / 1000) * price_info["output"]
        total_cost = input_cost + output_cost
        
        # Add to buffer
        self.buffer.append({
            "message_id": message_id,
            "project_id": span.get("project_id", "unknown"),
            "model": model,
            "span_kind": "llm",
            "timestamp": span.get("start_time", 0) // 1_000_000_000, # Convert ns to seconds
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": total_cost
        })

    async def flush_buffer(self):
        if not self.buffer:
            self.last_flush = time.time()
            return
            
        rows = []
        message_ids = []
        
        for item in self.buffer:
            message_ids.append(item["message_id"])
            rows.append([
                item["project_id"],
                item["model"],
                item["span_kind"],
                item["timestamp"], # DateTime64/Int64
                item["prompt_tokens"],
                item["completion_tokens"],
                item["total_tokens"],
                item["cost_usd"]
            ])
            
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._insert_sync, rows)
            
            # ACK processed messages for this consumer group
            pipeline = self.redis.pipeline()
            for msg_id in message_ids:
                pipeline.xack(self.stream_key, self.group_name, msg_id)
            await pipeline.execute()
            
            logger.info(f"Recorded costs for {len(rows)} spans")
            
        except Exception as e:
            logger.error(f"Failed to flush costs: {e}")
            # Don't clear buffer  retain data for retry on next flush cycle
            return

        self.buffer = []
        self.last_flush = time.time()

    def _insert_sync(self, rows):
        self.ch_client.insert(
            "cost_metrics",
            rows,
            column_names=[
                "project_id", "model", "span_kind", "timestamp",
                "prompt_tokens", "completion_tokens", "total_tokens", "cost_usd"
            ]
        )

if __name__ == "__main__":
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ch_host = os.getenv("CLICKHOUSE_HOST", "localhost")
    ch_user = os.getenv("CLICKHOUSE_USER", "default")
    ch_pass = os.getenv("CLICKHOUSE_PASSWORD", "")
    
    worker = CostCalculator(
        redis_url=redis_url, 
        clickhouse_host=ch_host,
        clickhouse_user=ch_user,
        clickhouse_password=ch_pass
    )
    asyncio.run(worker.start())
