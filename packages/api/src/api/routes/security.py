# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Security alert routes — query alerts by severity and project."""

from __future__ import annotations

import json
import aiosqlite
from fastapi import APIRouter, Depends, Query

from api.db_clickhouse import get_clickhouse, ClickHouseClient
from api.schemas import SecurityAlertSchema, SecurityAlertSeverity

router = APIRouter()


@router.get("/security/alerts", response_model=list[SecurityAlertSchema])
async def list_security_alerts(
    project_id: str | None = Query(None),
    severity: SecurityAlertSeverity | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    ch: ClickHouseClient = Depends(get_clickhouse),
):
    """List security alerts with optional filters.

    Filters: project_id, severity.
    Returns most recent alerts first.
    """
    filters = []
    params = {}

    if project_id:
        filters.append("project_id = {project_id:String}")
        params["project_id"] = project_id

    if severity:
        filters.append("severity = {severity:String}")
        params["severity"] = severity.value

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    query = f"""
        SELECT id, trace_id, span_id, project_id, severity, rule_name as alert_type, message, metadata, created_at
        FROM security_alerts
        {where_sql}
        ORDER BY created_at DESC
        LIMIT {limit}
    """

    rows = await ch.execute(query, params)

    alerts = []
    for row in rows:
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        alerts.append(
            SecurityAlertSchema(
                id=row["id"],
                trace_id=row["trace_id"],
                span_id=row["span_id"],
                project_id=row["project_id"],
                severity=SecurityAlertSeverity(row["severity"].lower()), # Normalize case
                alert_type=row["alert_type"],
                message=row["message"],
                metadata=metadata,
                created_at=row["created_at"],
            )
        )

    return alerts
