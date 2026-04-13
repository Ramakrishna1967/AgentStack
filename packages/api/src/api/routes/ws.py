# Copyright 2026 AgentStack Contributors
# SPDX-License-Identifier: Apache-2.0

"""WebSocket endpoint for real-time trace streaming and alerts."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis

router = APIRouter()
logger = logging.getLogger("agentstack.api")

# Connected WebSocket clients
_connections: Set[WebSocket] = set()

# Redis Consumer for Live Updates
redis_client: Redis | None = None
consumer_task: asyncio.Task | None = None


async def start_ws_consumer():
    """Start the Redis consumer background task."""
    global redis_client, consumer_task
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = Redis.from_url(redis_url, decode_responses=True)
    
    # Start consumer loop
    consumer_task = asyncio.create_task(consume_stream())
    logger.info("WebSocket Redis consumer started")


async def stop_ws_consumer():
    """Stop the Redis consumer."""
    global redis_client, consumer_task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass
            
    if redis_client:
        await redis_client.close()
        
    redis_client = None
    consumer_task = None
        
    logger.info("WebSocket Redis consumer stopped")


async def consume_stream():
    """Read from Redis streams and broadcast."""
    stream_key = "alerts.live"
    last_id = "$"
    
    while True:
        try:
            # XREAD from stream. Block for 1s.
            streams = await redis_client.xread(
                {stream_key: last_id}, count=10, block=1000
            )

            if not streams:
                continue

            for _, messages in streams:
                for message_id, data in messages:
                    last_id = message_id
                    # Broadcast alert
                    # Data is a dict. We wrap it in a WS message.
                    # Redis XREAD returns dict like {'id': ..., 'rule': ...}
                    
                    ws_msg = {
                        "type": "alert",
                        "data": data
                    }
                    await broadcast(ws_msg)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in WS consumer: {e}")
            await asyncio.sleep(1.0)


async def broadcast(message: dict) -> None:
    """Broadcast a message to all connected WebSocket clients."""
    if not _connections:
        return

    data = json.dumps(message)
    disconnected = set()

    for ws in list(_connections):
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.add(ws)

    # Clean up disconnected clients
    _connections.difference_update(disconnected)


@router.websocket("/ws/traces")
async def ws_trace_feed(websocket: WebSocket, token: str | None = None):
    """WebSocket endpoint with JWT authentication.
    
    Streams:
    1. Traces (future implementation via Redis PubSub or similar)
    2. Alerts (via Redis Stream consumer)
    
    Args:
        token: JWT token can be passed as query parameter ?token=xxx
    """
    # Validate JWT token before accepting connection
    from api.dependencies import get_current_user
    from jose import jwt, JWTError
    from api.config import settings
    
    try:
        # Try to get token from query param or subprotocol
        if not token:
            token = websocket.query_params.get("token")
        
        if not token and not settings.DEMO_MODE:
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        if token:
            try:
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
                user_id = payload.get("sub")
                if not user_id and not settings.DEMO_MODE:
                    await websocket.close(code=1008, reason="Invalid token")
                    return
            except JWTError:
                if not settings.DEMO_MODE:
                    await websocket.close(code=1008, reason="Invalid token")
                    return
        elif not settings.DEMO_MODE:
            await websocket.close(code=1008, reason="Authentication required")
            return
            
    except Exception:
        if not settings.DEMO_MODE:
            await websocket.close(code=1011, reason="Internal error")
            return
    
    await websocket.accept()
    _connections.add(websocket)
    logger.info("WebSocket client connected. Total: %d", len(_connections))

    try:
        while True:
            # Listen for ping/filters
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # --- HIGH-3 FIX: Reject oversized messages ---
                if len(data) > 4096:
                    await websocket.close(code=1009, reason="Message too large")
                    break

                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON on websocket")
                    # Send an error back instead of closing
                    await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON format"}))
                    continue

                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket error: %s", type(e).__name__)
    finally:
        _connections.discard(websocket)
        if websocket in _connections:
            _connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(_connections))

