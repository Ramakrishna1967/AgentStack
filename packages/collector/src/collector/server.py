# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Collector server — trace ingestion endpoint."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

import aiosqlite
from fastapi import FastAPI, Request, Depends, Header, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from collector.db import get_db
from collector.auth import verify_api_key
from collector.health import router as health_router
from collector.redis_writer import redis_writer
from collector.validators import (
    validate_span,
    check_payload_size,
    validate_payload,
)

logger = logging.getLogger("agentstack.collector")

# --- Rate limiting (100 req/min per IP) ---
_rl_store: dict[str, list[float]] = defaultdict(list)
_rl_lock = asyncio.Lock()
_RL_MAX = 100
_RL_WINDOW = 60


async def _rate_limit_middleware(request: Request, call_next: Callable):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    async with _rl_lock:
        _rl_store[client_ip] = [t for t in _rl_store[client_ip] if now - t < _RL_WINDOW]
        if len(_rl_store[client_ip]) >= _RL_MAX:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        _rl_store[client_ip].append(now)
    return await call_next(request)


# --- Security: Max payload size (5MB compressed, 50MB decompressed) ---
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 50 * 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    logger.info("Collector starting...")

    # Wait for API to initialize DB if needed
    # The collector assumes the API service handles migrations.
    logger.info("Database connection configured")

    # Initialize Redis Writer
    await redis_writer.connect()
    logger.info("Redis writer connected")

    yield

    await redis_writer.close()
    logger.info("Collector shutting down...")


app = FastAPI(
    title="AgentStack Collector",
    description="Trace ingestion endpoint for AgentStack SDK",
    version="0.1.0-alpha",
    lifespan=lifespan,
)

# --- CRIT-4 FIX: Locked-down CORS ---
_allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

# Rate limiting — register before CORS so CORS is outermost and adds headers to 429s
app.middleware("http")(_rate_limit_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _allowed_origins],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "X-API-Key", "Content-Encoding"],
)

# Include health routes
app.include_router(health_router, tags=["system"])


@app.post("/v1/traces", status_code=202)
async def ingest_traces(
    request: Request,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Ingest trace spans from SDK.

    - Validates API key
    - Validates payload schema
    - Rejects payloads > 5MB (checks actual body, not Content-Length header)
    - Pushes spans to Redis Stream (spans.ingest)
    - Returns 202 Accepted on success
    """
    # --- HIGH-4 FIX: Check actual body size, not Content-Length header ---
    body_bytes = await request.body()
    if len(body_bytes) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large (max 5MB)")

    # Handle compression
    content_encoding = request.headers.get("Content-Encoding", "").lower()
    if content_encoding == "gzip":
        try:
            import gzip, io
            with gzip.GzipFile(fileobj=io.BytesIO(body_bytes)) as gz:
                body_bytes = gz.read(MAX_DECOMPRESSED_BYTES + 1)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid gzip payload")
        if len(body_bytes) > MAX_DECOMPRESSED_BYTES:
            raise HTTPException(status_code=413, detail="Decompressed payload too large (max 50MB)")

    # Verify API key and get project_id
    project_id = await verify_api_key(x_api_key=x_api_key, db=db)

    # Parse payload
    try:
        body = json.loads(body_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Handle batch or single span
    spans_input = body.get("spans", []) if isinstance(body, dict) else (body if isinstance(body, list) else [body])
    if not isinstance(spans_input, list):
        spans_input = [spans_input]

    queued_count = 0
    for span_data in spans_input:
        # Basic schema validation
        try:
            validate_span(span_data)
        except ValueError as e:
            logger.warning("Invalid span dropped: %s", e)
            continue

        span_data["project_id"] = project_id

        # Async write to Redis
        await redis_writer.add_span(span_data)
        queued_count += 1

    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "spans_queued": queued_count,
            "project_id": project_id,
        },
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "collector.server:app",
        host="0.0.0.0",
        port=4318,
        reload=True,
        log_level="info",
    )
