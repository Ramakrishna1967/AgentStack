# Copyright 2026 Oxly Contributors
# SPDX-License-Identifier: Apache-2.0

"""WebSocket endpoint tests using TestClient."""

from __future__ import annotations

import json
from fastapi.testclient import TestClient

def test_ws_connect(app):
    """Test basic WebSocket connection and ping/pong."""
    client = TestClient(app)
    with client.websocket_connect("/ws/traces") as websocket:
        # Send ping
        websocket.send_text(json.dumps({"type": "ping"}))
        data = websocket.receive_json()
        assert data["type"] == "pong"

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
