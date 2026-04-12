# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

from fastapi import APIRouter, Depends
from api.db_clickhouse import get_clickhouse, ClickHouseClient
import redis.asyncio as redis
import os

router = APIRouter()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@router.get("/health")
async def health_check(ch: ClickHouseClient = Depends(get_clickhouse)):
    """Check connectivity to downstream services."""
    ch_ok = await ch.check_health()
    
    redis_ok = False
    try:
        r = redis.from_url(REDIS_URL)
        await r.ping()
        redis_ok = True
    except Exception:
        pass

    return {
        "status": "healthy" if ch_ok and redis_ok else "degraded",
        "services": {
            "clickhouse": "operational" if ch_ok else "down",
            "redis": "operational" if redis_ok else "down",
            "collector": "operational", # Assume up if we're here
            "worker": "operational"     # Generic assumption
        }
    }
