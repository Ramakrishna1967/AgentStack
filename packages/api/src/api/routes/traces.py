# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Trace routes — list traces, get trace detail with full span tree."""

from __future__ import annotations

import json
import time
import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List

from api.db import get_db
from api.db_clickhouse import get_clickhouse, ClickHouseClient
from api.dependencies import get_current_active_user
from api.schemas import TraceSchema, TraceDetailSchema, SpanSchema, SpanStatus

router = APIRouter()


@router.get("/traces", response_model=dict)
async def list_traces(
    project_id: str | None = Query(None),
    status: str | None = Query(None),
    start_date: int | None = Query(None, description="Unix timestamp in nanoseconds"),
    end_date: int | None = Query(None, description="Unix timestamp in nanoseconds"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    ch: ClickHouseClient = Depends(get_clickhouse),
    db: aiosqlite.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """List traces with pagination and filters by querying ClickHouse spans."""
    # Build query
    filters = []
    params = {}

    if project_id:
        async with db.execute(
            "SELECT 1 FROM user_projects WHERE user_id = ? AND project_id = ?",
            (current_user["id"], project_id),
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=403, detail="Project not found")
    else:
        async with db.execute(
            "SELECT project_id FROM user_projects WHERE user_id = ?",
            (current_user["id"],),
        ) as cursor:
            owned_ids = [row[0] for row in await cursor.fetchall()]
        if not owned_ids:
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}
        placeholders = ", ".join(f"'{pid}'" for pid in owned_ids)
        filters.append(f"project_id IN ({placeholders})")

    if project_id:
        filters.append("project_id = {project_id:String}")
        params["project_id"] = project_id

    if status:
        filters.append("status = {status:String}")
        params["status"] = status

    # start_date/end_date are in nanoseconds (Unix nano)
    # ClickHouse start_time is DateTime64(6) - microseconds
    if start_date:
        filters.append("start_time >= {start_date:Int64} / 1000")
        params["start_date"] = start_date

    if end_date:
        filters.append("start_time <= {end_date:Int64} / 1000")
        params["end_date"] = end_date

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    # Group spans into traces
    inner_query = f"""
        SELECT 
            trace_id, 
            project_id, 
            min(start_time) as start_time, 
            max(end_time) as end_time, 
            count(*) as span_count,
            any(status) as status
        FROM spans
        {where_sql}
        GROUP BY trace_id, project_id
    """

    # Get total count (number of unique trace_ids)
    count_query = f"SELECT count() as total FROM ({inner_query})"
    count_res = await ch.execute(count_query, params)
    total = count_res[0]['total'] if count_res else 0

    # Fetch paginated results
    offset = (page - 1) * page_size
    query = f"""
        SELECT * FROM ({inner_query})
        ORDER BY start_time DESC
        LIMIT {page_size} OFFSET {offset}
    """
    rows = await ch.execute(query, params)

    traces = []
    for row in rows:
        # HIGH-5 FIX: Robust timestamp conversion to avoid 'year out of range' crashes
        try:
            start_ns = int(row["start_time"].timestamp() * 1e9)
        except (ValueError, OverflowError, AttributeError):
            start_ns = int(time.time() * 1e9) # Fallback to now
            
        try:
            end_ns = int(row["end_time"].timestamp() * 1e9)
        except (ValueError, OverflowError, AttributeError):
            end_ns = start_ns + 1000 # Minimal duration fallback

        traces.append({
            "trace_id": row["trace_id"],
            "project_id": row["project_id"],
            "start_time": start_ns,
            "end_time": end_ns,
            "duration_ms": (end_ns - start_ns) / 1e6,
            "status": row["status"],
            "span_count": row["span_count"],
        })

    return {
        "items": traces,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/traces/{trace_id}", response_model=TraceDetailSchema)
async def get_trace_detail(
    trace_id: str,
    ch: ClickHouseClient = Depends(get_clickhouse),
    db: aiosqlite.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Get full trace detail with all spans from ClickHouse."""
    # Fetch all spans for trace
    query = "SELECT * FROM spans WHERE trace_id = {trace_id:String} ORDER BY start_time ASC"
    span_rows = await ch.execute(query, {"trace_id": trace_id})

    if not span_rows:
        raise HTTPException(status_code=404, detail="Trace not found")

    trace_project_id = span_rows[0]["project_id"]
    async with db.execute(
        "SELECT 1 FROM user_projects WHERE user_id = ? AND project_id = ?",
        (current_user["id"], trace_project_id),
    ) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=403, detail="Trace not found")

    spans = []
    min_start = None
    max_end = None
    final_status = SpanStatus.OK

    for row in span_rows:
        start_ns = int(row["start_time"].timestamp() * 1e9)
        end_ns = int(row["end_time"].timestamp() * 1e9)
        
        if min_start is None or start_ns < min_start: min_start = start_ns
        if max_end is None or end_ns > max_end: max_end = end_ns
        if row["status"] == "ERROR": final_status = SpanStatus.ERROR

        spans.append(
            SpanSchema(
                span_id=row["span_id"],
                trace_id=row["trace_id"],
                parent_span_id=row["parent_span_id"] or None,
                name=row["name"],
                start_time=start_ns,
                end_time=end_ns,
                duration_ms=row["duration_ms"],
                status=SpanStatus(row["status"]),
                service_name=row["service_name"] or "default",
                attributes=row["attributes"],
                events=json.loads(row["events"]) if row["events"] else [],
                project_id=row["project_id"],
            )
        )

    return TraceDetailSchema(
        trace_id=trace_id,
        project_id=span_rows[0]["project_id"],
        start_time=min_start,
        end_time=max_end,
        duration_ms=(max_end - min_start) / 1e6 if min_start and max_end else 0,
        status=final_status,
        spans=spans,
    )

@router.get("/traces/{trace_id}/replay", response_model=List[SpanSchema])
async def get_trace_replay(
    trace_id: str,
    ch: ClickHouseClient = Depends(get_clickhouse),
    db: aiosqlite.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Get ordered spans for a trace to support Time Machine replay."""
    query = "SELECT * FROM spans WHERE trace_id = {trace_id:String} ORDER BY start_time ASC"
    span_rows = await ch.execute(query, {"trace_id": trace_id})

    if not span_rows:
        raise HTTPException(status_code=404, detail="Trace not found or contains no spans")

    trace_project_id = span_rows[0]["project_id"]
    async with db.execute(
        "SELECT 1 FROM user_projects WHERE user_id = ? AND project_id = ?",
        (current_user["id"], trace_project_id),
    ) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=403, detail="Trace not found")

    spans = []
    for row in span_rows:
        start_ns = int(row["start_time"].timestamp() * 1e9)
        end_ns = int(row["end_time"].timestamp() * 1e9)
        attributes = row["attributes"] if isinstance(row["attributes"], dict) else {}
        events = json.loads(row["events"]) if row["events"] else []

        spans.append(
            SpanSchema(
                span_id=row["span_id"],
                trace_id=row["trace_id"],
                parent_span_id=row["parent_span_id"] or None,
                name=row["name"],
                start_time=start_ns,
                end_time=end_ns,
                duration_ms=row["duration_ms"],
                status=SpanStatus(row["status"]),
                service_name=row["service_name"] or "default",
                attributes=attributes,
                events=events,
                project_id=row["project_id"],
            )
        )

    return spans
