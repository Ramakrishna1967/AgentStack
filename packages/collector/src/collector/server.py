# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Collector server  trace ingestion endpoint."""

from __future__ import annotations

import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

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

# --- Security: Max payload size (5MB) ---
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024


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
            import gzip
            body_bytes = gzip.decompress(body_bytes)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid gzip payload")

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

        # Enrich with project_id
        # --- AUTO-DISCOVERY: If trace has a custom project_id, try to use it ---
        trace_project_id = span_data.get("project_id") or project_id
        span_data["project_id"] = trace_project_id

        # Async: Ensure project exists in SQLite so it shows in Dashboard
        try:
            # Check if this project is already known to the cache or DB
            # We'll do a simple 'INSERT OR IGNORE' to keep it fast
            await db.execute(
                "INSERT OR IGNORE INTO projects (id, name, api_key_hash) VALUES (?, ?, ?)",
                (trace_project_id, trace_project_id.replace('-', ' ').title(), x_api_key)
            )
            await db.commit()
        except Exception as e:
            logger.debug("Optional project auto-create failed: %s", e)

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
