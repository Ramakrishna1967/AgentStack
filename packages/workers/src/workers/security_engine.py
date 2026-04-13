# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import logging
import json
import uuid
import time
from typing import Dict, Any, List

from redis.asyncio import Redis
from clickhouse_connect import get_client
from clickhouse_connect.driver.client import Client as ClickHouseClient

from workers.consumer import BaseConsumer
from workers.rules import injection, pii, anomaly

logger = logging.getLogger(__name__)

class SecurityEngine(BaseConsumer):
    """Worker that scans spans for security threats."""

    def __init__(
        self,
        redis_url: str,
        clickhouse_host: str = "localhost",
        clickhouse_port: int = 8123,
        clickhouse_user: str = "default",
        clickhouse_password: str = "",
    ):
        super().__init__(
            redis_url=redis_url,
            stream_key="spans.ingest",
            group_name="security-group", # Separate group = independent reading
            consumer_name=f"worker-security-{uuid.uuid4().hex[:8]}",
            batch_size=10, 
        )
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.clickhouse_user = clickhouse_user
        self.clickhouse_password = clickhouse_password
        self.ch_client = None
        self.alerts_stream = "alerts.live"

    async def start(self):
        # Initialize ClickHouse client
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
            raise RuntimeError("Fatal: ClickHouse connection required for SecurityEngine")
        
        await super().start()

    async def process_message(self, message_id: bytes, data: Dict[bytes, bytes]):
        try:
            if b"data" not in data:
                return
                
            # Decode payload
            span = self.decode_msgpack(data[b"data"])
            await self.analyze_span(span)
            
        except Exception as e:
            logger.error(f"Error analyzing span {message_id}: {e}")
            raise

    async def analyze_span(self, span: dict):
        """Run security rules on span."""
        # Extract checkable text
        # Inputs, Outputs, System Prompts from attributes or events
        text_content = []
        
        attrs = span.get("attributes", {})
        
        # Check specific attribution keys for LLM I/O
        if "llm.prompts.0.content" in attrs:
            text_content.append(str(attrs["llm.prompts.0.content"]))
        if "llm.completions.0.content" in attrs:
            text_content.append(str(attrs["llm.completions.0.content"]))
        
        # Also check events for 'message' logs
        events = span.get("events", [])
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict) and "attributes" in event:
                    msg = event["attributes"].get("message", "")
                    if msg:
                        text_content.append(str(msg))
            
        # Combine text for analysis
        full_text = "\n".join(text_content)
        
        alerts = []
        
        # 1. Injection
        if full_text:
            injection_score = injection.check_injection(full_text)
            if injection_score > 50:
                alerts.append({
                    "rule": "Prompt Injection",
                    "severity": "HIGH" if injection_score > 80 else "MEDIUM",
                    "score": injection_score,
                    "description": "Potential prompt injection detected in LLM input/output",
                    "evidence": full_text[:200] # Truncate
                })
            
            # 2. PII
            pii_types = pii.check_pii(full_text)
            if pii_types:
                alerts.append({
                    "rule": "PII Leak",
                    "severity": "CRITICAL" if ("AWS_KEY" in pii_types or "SSN" in pii_types) else "HIGH",
                    "score": 100.0,
                    "description": f"Sensitive PII detected: {', '.join(pii_types)}",
                    "evidence": "REDACTED"
                })
            
        # 3. Anomalies (Logic in module)
        anomalies = anomaly.check_anomaly(span)
        for anom in anomalies:
            alerts.append({
                "rule": anom.split(":")[0], # "High token usage"
                "severity": "LOW",
                "score": 30.0,
                "description": anom,
                "evidence": str(span.get("duration_ms", "N/A"))
            })
            
        # Save alerts
        if alerts:
            await self.save_alerts(span, alerts)

    async def save_alerts(self, span: dict, alerts: list[dict]):
        """Persist alerts to ClickHouse and Redis Stream."""
        project_id = span.get("project_id", "unknown")
        trace_id = span.get("trace_id", "unknown")
        span_id = span.get("span_id", "unknown")
        
        rows = []
        timestamp = time.time()
        
        for alert in alerts:
            alert_id = str(uuid.uuid4())
            
            # ClickHouse row structure matching init.sql:
            # id, project_id, trace_id, span_id, rule_name, severity, score, description, evidence
            # created_at uses DEFAULT now() so it is omitted from insert
            rows.append([
                alert_id,
                project_id,
                trace_id,
                span_id,
                alert["rule"],
                alert["severity"],
                float(alert["score"]),
                alert["description"],
                alert["evidence"],
            ])
            
            # Real-time notification via Redis
            # Redis XADD requires all field values to be strings or bytes
            notification = {
                "id": alert_id,
                "project_id": str(project_id),
                "trace_id": str(trace_id),
                "span_id": str(span_id),
                "rule": str(alert["rule"]),
                "severity": str(alert["severity"]),
                "description": str(alert["description"]),
                "created_at": str(timestamp),
            }
            # Add to alerts stream
            await self.redis.xadd(self.alerts_stream, notification)
            
        if rows:
            if not self.ch_client:
                raise RuntimeError("Failed to save alerts: ClickHouse client is entirely missing.")
            
            # Sync insert to CH in executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._insert_sync, rows)
            logger.info(f"Generated {len(rows)} alerts for span {span_id[:8]}")

    def _insert_sync(self, rows):
        # We need to explicitly check column names against init.sql
        # init.sql: id, project_id, trace_id, span_id, rule_name, severity, score, description, evidence, (created_at DEFAULT)
        self.ch_client.insert(
            "security_alerts",
            rows,
            column_names=[
                "id", "project_id", "trace_id", "span_id", "rule_name",
                "severity", "score", "description", "evidence"
            ]
        )

if __name__ == "__main__":
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ch_host = os.getenv("CLICKHOUSE_HOST", "localhost")
    ch_user = os.getenv("CLICKHOUSE_USER", "default")
    ch_pass = os.getenv("CLICKHOUSE_PASSWORD", "")
    
    worker = SecurityEngine(
        redis_url=redis_url, 
        clickhouse_host=ch_host,
        clickhouse_user=ch_user,
        clickhouse_password=ch_pass
    )
    asyncio.run(worker.start())
