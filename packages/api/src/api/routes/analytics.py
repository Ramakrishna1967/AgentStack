# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Analytics routes — cost tracking and timeseries data."""

from __future__ import annotations

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal

from api.db import get_db
from api.dependencies import get_current_active_user
from api.db_clickhouse import get_clickhouse, ClickHouseClient

router = APIRouter()


@router.get("/analytics/cost")
async def get_cost_timeseries(
    project_id: str | None = Query(None),
    interval: Literal["hour", "day", "week"] = Query("day"),
    start_date: int | None = Query(None, description="Unix timestamp in seconds"),
    end_date: int | None = Query(None, description="Unix timestamp in seconds"),
    ch: ClickHouseClient = Depends(get_clickhouse),
    db: aiosqlite.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Get cost metrics over time from ClickHouse.

    Groups by time interval and sums cost_usd.
    """
    where_clauses = []
    params = []

    if project_id:
        async with db.execute(
            "SELECT 1 FROM user_projects WHERE user_id = ? AND project_id = ?",
            (current_user["id"], project_id),
        ) as cursor:
            if not await cursor.fetchone():
                raise HTTPException(status_code=403, detail="Project not found")
        where_clauses.append("project_id = %s")
        params.append(project_id)
    else:
        async with db.execute(
            "SELECT project_id FROM user_projects WHERE user_id = ?",
            (current_user["id"],),
        ) as cursor:
            owned_ids = [row[0] for row in await cursor.fetchall()]
        if not owned_ids:
            return {"interval": interval, "project_id": None, "data": []}
        placeholders = ", ".join(["%s"] * len(owned_ids))
        where_clauses.append(f"project_id IN ({placeholders})")
        params.extend(owned_ids)

    if start_date:
        where_clauses.append("timestamp >= toDateTime(%s)")
        params.append(start_date)

    if end_date:
        where_clauses.append("timestamp <= toDateTime(%s)")
        params.append(end_date)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    # Time bucket function
    if interval == "hour":
        time_func = "toStartOfHour(timestamp)"
    elif interval == "day":
        time_func = "toStartOfDay(timestamp)"
    else:
        time_func = "toStartOfWeek(timestamp)"

    query = f"""
        SELECT
            {time_func} AS time_bucket,
            model,
            SUM(prompt_tokens) as prompt_tokens,
            SUM(completion_tokens) as completion_tokens,
            SUM(total_tokens) as total_tokens,
            SUM(cost_usd) as cost_usd
        FROM cost_metrics
        {where_sql}
        GROUP BY time_bucket, model
        ORDER BY time_bucket ASC
    """

    try:
        rows = await ch.execute(query, params if params else None)
    except Exception as e:
        # If table doesn't exist or other error, return empty
        return {"data": []}

    # Format for frontend
    # Recharts expects array of objects. We might want to group by timestamp.
    # [{timestamp: ..., "gpt-4": 1.2, "claude-3": 0.5}, ...]
    
    processed = {}
    
    for row in rows:
        bucket = row["time_bucket"] # DateTime
        # Convert to ISO string or timestamp
        ts = bucket.isoformat() if hasattr(bucket, 'isoformat') else str(bucket)
        
        if ts not in processed:
            processed[ts] = {"timestamp": ts, "total_cost": 0}
            
        model = row["model"]
        cost = row["cost_usd"]
        
        processed[ts][model] = cost
        processed[ts]["total_cost"] += cost
        
    results = list(processed.values())
    
    return {
        "interval": interval,
        "project_id": project_id,
        "data": results,
    }
