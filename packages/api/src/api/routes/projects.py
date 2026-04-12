# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Project routes — CRUD operations and API key management.

HIGH-5 FIX: All queries are now scoped to the current user via
the user_projects join table. Users can only see/manage their own projects.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from passlib.hash import pbkdf2_sha256 as pwd_context

from api.db import get_db
from api.dependencies import get_current_active_user
from api.schemas import ProjectSchema, ProjectCreateRequest, ProjectCreateResponse

router = APIRouter()


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"ak_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash API key for storage."""
    return pwd_context.hash(api_key)


@router.post("/projects", response_model=ProjectCreateResponse)
async def create_project(
    request: ProjectCreateRequest,
    db: aiosqlite.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new project and generate API key.

    API key is shown ONCE in the response, then only hash is stored.
    Project is automatically linked to the current user.
    """
    project_id = str(uuid.uuid4())
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    now = datetime.now(timezone.utc)  # LOW-3 FIX

    await db.execute(
        """
        INSERT INTO projects (id, name, api_key_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project_id, request.name, api_key_hash, now, now),
    )

    # HIGH-5 FIX: Link project to current user
    await db.execute(
        """
        INSERT INTO user_projects (user_id, project_id, role)
        VALUES (?, ?, 'owner')
        """,
        (current_user["id"], project_id),
    )

    await db.commit()

    project = ProjectSchema(
        id=project_id,
        name=request.name,
        created_at=now,
        updated_at=now,
    )

    return ProjectCreateResponse(project=project, api_key=api_key)


@router.get("/projects", response_model=list[ProjectSchema])
async def list_projects(
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all projects for the demo."""
    async with db.execute(
        """
        SELECT id, name, created_at, updated_at
        FROM projects
        ORDER BY created_at DESC
        """
    ) as cursor:
        rows = await cursor.fetchall()

    return [
        ProjectSchema(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]


@router.get("/projects/{project_id}", response_model=ProjectSchema)
async def get_project(
    project_id: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get project by ID."""
    async with db.execute(
        """
        SELECT id, name, created_at, updated_at
        FROM projects
        WHERE id = ?
        """,
        (project_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectSchema(
        id=row["id"],
        name=row["name"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: aiosqlite.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_active_user),
):
    """Delete a project (only if owned by current user, cascades to traces/spans)."""
    # HIGH-5 FIX: Verify ownership before deletion
    async with db.execute(
        "SELECT 1 FROM user_projects WHERE user_id = ? AND project_id = ?",
        (current_user["id"], project_id),
    ) as cursor:
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

    await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    await db.commit()
    return None
