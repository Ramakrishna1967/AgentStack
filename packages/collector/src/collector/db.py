# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Minimal SQLite connection for the Collector.

Decouples the Collector from the API package. The Collector only needs
read access to the projects table for API key verification.
"""

import os
import aiosqlite
from typing import AsyncGenerator

# Use shared DB path via environment variable or default
def _get_db_path() -> str:
    db_url = os.getenv("DATABASE_URL", "agentstack.db")
    if db_url.startswith("sqlite"):
        if "////" in db_url:
            return "/" + db_url.split("////")[-1]
        elif "///" in db_url:
            path_str = db_url.split("///")[-1]
            if path_str.startswith("/"):
                return path_str
            return os.path.join("/app", path_str)
    return os.getenv("AGENTSTACK_DB_PATH", "/app/agentstack.db")

_db_path = _get_db_path()

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Dependency injection: get database connection for FastAPI routes."""
    conn = await aiosqlite.connect(_db_path, timeout=5.0)
    conn.row_factory = aiosqlite.Row
    try:
        # Enforce pragmatic settings for read performance
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA busy_timeout=5000")
        yield conn
    finally:
        await conn.close()
