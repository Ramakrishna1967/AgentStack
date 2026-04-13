# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Health check endpoint with dependency status reporting."""

from __future__ import annotations

import aiosqlite
from fastapi import APIRouter, Depends
from api.db_clickhouse import get_clickhouse, ClickHouseClient
from api.db import get_database
from api.config import settings
import redis.asyncio as redis
import os
import time

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_START_TIME = time.time()


@router.get("/health")
async def health_check(ch: ClickHouseClient = Depends(get_clickhouse)):
    """Check connectivity to all downstream services.

    Returns individual service status and overall health.
    """
    # ClickHouse
    ch_ok = await ch.check_health()

    # Redis (with proper connection cleanup)
    redis_ok = False
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        redis_ok = True
        await r.close()
    except Exception:
        pass

    # SQLite (API's own database)
    sqlite_ok = False
    try:
        db = get_database()
        conn = await db.get_connection()
        await conn.execute("SELECT 1")
        sqlite_ok = True
        await conn.close()
    except Exception:
        pass

    all_ok = ch_ok and redis_ok and sqlite_ok
    any_ok = ch_ok or redis_ok or sqlite_ok

    return {
        "status": "healthy" if all_ok else ("degraded" if any_ok else "down"),
        "version": "0.1.0-alpha",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "environment": settings.ENVIRONMENT,
        "services": {
            "clickhouse": "operational" if ch_ok else "down",
            "redis": "operational" if redis_ok else "down",
            "sqlite": "operational" if sqlite_ok else "down",
        }
    }
