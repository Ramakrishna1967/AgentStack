# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

import logging
import re
from typing import AsyncGenerator, Any
from asynch import Connection
from asynch.cursors import DictCursor

import os

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = os.getenv("CLICKHOUSE_NATIVE_PORT", "9000")
CLICKHOUSE_DB = os.getenv("CLICKHOUSE_DB", "default")
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

CLICKHOUSE_URL = f"clickhouse://{CLICKHOUSE_USER}:{CLICKHOUSE_PASSWORD}@{CLICKHOUSE_HOST}:{CLICKHOUSE_PORT}/{CLICKHOUSE_DB}"

logger = logging.getLogger("agentstack.api.clickhouse")


def _escape_string(value: str) -> str:
    """Escape a string value for safe inline use in ClickHouse SQL."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _build_query(query: str, params: dict | None) -> str:
    """
    Replace {key:Type} placeholders with safely escaped literal values.
    Supports String, Int64, Float64 types.
    """
    if not params:
        return query

    def replacer(match):
        key = match.group(1)
        typ = match.group(2)
        val = params.get(key)
        if val is None:
            return "NULL"
        if typ == "String":
            return f"'{_escape_string(str(val))}'"
        elif typ in ("Int64", "Int32", "UInt64", "Float64"):
            return str(val)
        return f"'{_escape_string(str(val))}'"

    return re.sub(r"\{(\w+):(\w+)\}", replacer, query)


class ClickHouseClient:
    """Async ClickHouse client wrapper."""

    def __init__(self, dsn: str = CLICKHOUSE_URL):
        self.dsn = dsn

    async def execute(self, query: str, params: dict | None = None) -> list[dict]:
        """Execute a query and return dict results."""
        final_query = _build_query(query, params)
        async with Connection(dsn=self.dsn) as conn:
            async with conn.cursor(cursor=DictCursor) as cursor:
                await cursor.execute(final_query)
                return await cursor.fetchall()

    async def check_health(self) -> bool:
        """Check connection health."""
        try:
            res = await self.execute("SELECT 1 as val")
            return len(res) > 0
        except Exception as e:
            logger.error(f"ClickHouse health check failed: {e}")
            return False


# Global instance
ch_client = ClickHouseClient()


async def get_clickhouse() -> AsyncGenerator[ClickHouseClient, None]:
    """Dependency for FastAPI."""
    yield ch_client
