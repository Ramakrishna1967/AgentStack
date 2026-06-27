# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""Dependency injection for FastAPI routes."""

from __future__ import annotations

import aiosqlite
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import AsyncGenerator

from api.db import get_db

# JWT configuration
from api.config import settings

# JWT configuration
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict | None:
    """Get current authenticated user (Optional for demo)."""
    if not credentials:
        if settings.DEMO_MODE:
            return {"id": "demo", "email": "demo@agentstack.sh", "is_active": True}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
             if settings.DEMO_MODE:
                return {"id": "demo", "email": "demo@agentstack.sh", "is_active": True}
             raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        if settings.DEMO_MODE:
            return {"id": "demo", "email": "demo@agentstack.sh", "is_active": True}
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch user from database
    async with db.execute(
        "SELECT id, email, is_active FROM users WHERE id = ?",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user = dict(row)
    return user


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get current active user."""
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user
