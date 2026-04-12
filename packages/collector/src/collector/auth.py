# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""API key validation for collector authentication.

HIGH-1 FIX: Uses SHA-256 fast hash for O(1) lookup instead of
scanning all projects with slow pbkdf2 verify on each row.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

import aiosqlite
from fastapi import HTTPException, Header, Depends
from passlib.hash import pbkdf2_sha256 as pwd_context

logger = logging.getLogger("agentstack.collector")

# --- HIGH-1 FIX: In-memory cache for verified keys ---
# Maps fast_hash(api_key) -> project_id
# Avoids repeated slow pbkdf2 verification for known-good keys.
_verified_keys_cache: dict[str, str] = {}
_CACHE_MAX_SIZE = 1000


def _fast_hash(api_key: str) -> str:
    """Compute a fast SHA-256 hash for cache lookup."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: aiosqlite.Connection = Depends(),
) -> str:
    """Verify API key and return project_id.

    Uses a two-tier approach:
    1. Fast path: SHA-256 cache lookup (O(1), <1ms)
    2. Slow path: Full pbkdf2 scan (only on first use of a key)

    Returns the project_id if valid.
    Raises 401 if invalid.
    """
    if not x_api_key or not x_api_key.startswith("ak_"):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key format",
        )

    # --- Fast path: check cache ---
    fast_key = _fast_hash(x_api_key)
    cached_project_id = _verified_keys_cache.get(fast_key)
    if cached_project_id is not None:
        return cached_project_id

    # --- Slow path: scan all projects (first-time verification) ---
    async with db.execute("SELECT id, api_key_hash FROM projects") as cursor:
        rows = await cursor.fetchall()

    loop = asyncio.get_event_loop()

    for row in rows:
        # Offload slow pbkdf2 verification to the thread pool executor
        # to prevent blocking the async event loop and causing a DoS.
        is_valid = await loop.run_in_executor(
            None, pwd_context.verify, x_api_key, row["api_key_hash"]
        )
        if is_valid:
            project_id = row["id"]

            # Cache the result for future fast lookups
            if len(_verified_keys_cache) < _CACHE_MAX_SIZE:
                _verified_keys_cache[fast_key] = project_id

            return project_id

    # --- AUTO-DISCOVERY: If key is the demo key, allow dynamic project IDs ---
    # In a real prod environment, we would only allow this for specific tiers.
    # For this platform, we'll allow it if the key is the standard demo key.
    if x_api_key == "ak_agentstack_demo_key_2026":
        # We need to know which project the user WANTED. 
        # Since the SDK sends it in the payload, we'll return a special 'DYNAMIC' flag
        # and handle the creation in server.py after parsing the payload.
        # OR, we can just return 'demo-simulation' as the default and let the trace enrichment handle it.
        # Actually, let's just return 'demo-simulation' but allow server.py to override.
        return "demo-simulation"

    raise HTTPException(
        status_code=401,
        detail="Invalid API key",
    )


def invalidate_key_cache(api_key: str | None = None) -> None:
    """Invalidate the key cache (call on project deletion)."""
    if api_key:
        _verified_keys_cache.pop(_fast_hash(api_key), None)
    else:
        _verified_keys_cache.clear()
