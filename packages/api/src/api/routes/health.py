# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Health check endpoint with dependency status reporting."""

from __future__ import annotations

import time

from fastapi import APIRouter

from api.config import settings
from api.db import get_database

router = APIRouter()

_START_TIME = time.time()


@router.get("/health")
async def health_check():
    """Check connectivity to all downstream services.

    Returns individual service status and overall health.
    """
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

    return {
        "status": "healthy" if sqlite_ok else "down",
        "version": "0.1.0-alpha",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "environment": settings.ENVIRONMENT,
        "services": {
            "sqlite": "operational" if sqlite_ok else "down",
        }
    }
