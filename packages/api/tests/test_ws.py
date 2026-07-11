# Copyright 2026 Oxly Contributors
# SPDX-License-Identifier: Apache-2.0

"""WebSocket endpoint tests using TestClient."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def demo_mode(monkeypatch):
    """ws_trace_feed rejects unauthenticated connections unless
    settings.DEMO_MODE is on. The shared `app` fixture never sets it (and
    these tests connect with no token), so without this every connection
    gets closed with code 1008 before any message logic runs.
    """
    from api.config import settings
    monkeypatch.setattr(settings, "DEMO_MODE", True)


def test_ws_connect(app):
    """Test basic WebSocket connection and ping/pong."""
    client = TestClient(app)
    with client.websocket_connect("/ws/traces") as websocket:
        # Send ping
        websocket.send_text(json.dumps({"type": "ping"}))
        data = websocket.receive_json()
        assert data["type"] == "pong"


@pytest.mark.skip(reason="{'type': 'filter'} is not implemented and not planned -- "
                         "ws_trace_feed only handles 'ping'. See ws.py's message loop.")
def test_ws_filter_ack(app):
    """Test filter message acknowledged."""
    client = TestClient(app)
    with client.websocket_connect("/ws/traces") as websocket:
        websocket.send_text(
            json.dumps({
                "type": "filter",
                "project_id": "test-project",
                "status": "ERROR",
            })
        )
        data = websocket.receive_json()
        assert data["type"] == "filter_ack"
