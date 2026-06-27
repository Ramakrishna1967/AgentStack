# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Span routes  individual span detail."""

from __future__ import annotations

import json
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from api.db_clickhouse import get_clickhouse, ClickHouseClient
from api.dependencies import get_current_active_user
from api.schemas import SpanSchema, SpanStatus

router = APIRouter()


@router.get("/spans/{span_id}", response_model=SpanSchema)
async def get_span_detail(
    span_id: str,
    ch: ClickHouseClient = Depends(get_clickhouse),
):
    """Get individual span detail by ID from ClickHouse."""
    query = "SELECT * FROM spans WHERE span_id = {span_id:String}"
    rows = await ch.execute(query, {"span_id": span_id})

    if not rows:
        raise HTTPException(status_code=404, detail="Span not found")

    row = rows[0]

    return SpanSchema(
        span_id=row["span_id"],
        trace_id=row["trace_id"],
        parent_span_id=row["parent_span_id"] or None,
        name=row["name"],
        start_time=int(row["start_time"].timestamp() * 1e9),
        end_time=int(row["end_time"].timestamp() * 1e9),
        duration_ms=row["duration_ms"],
        status=SpanStatus(row["status"]),
        service_name=row["service_name"] or "default",
        attributes=row["attributes"],
        events=json.loads(row["events"]) if row["events"] else [],
        project_id=row["project_id"],
    )
