"""Smoke tests for yuanfang-brain server."""

import pytest
from fastapi.testclient import TestClient

from yuanfang_brain.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_version(client):
    resp = client.get("/version")
    assert resp.status_code == 200
    assert "version" in resp.json()


def test_metrics(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "requests_total" in data


def test_ws_endpoint(client):
    """WebSocket endpoint accepts connection and sends hello on connect."""
    with client.websocket_connect("/ws") as ws:
        # Server sends hello immediately on connect
        data = ws.receive_json()
        assert data["type"] == "hello"
        assert data["data"]["server"] == "yuanfang-brain"


def test_ws_ping(client):
    """WebSocket responds to ping with pong."""
    with client.websocket_connect("/ws") as ws:
        # Receive the server hello first
        ws.receive_json()
        # Now send ping and expect pong
        ws.send_json({"type": "ping", "trace_id": "test-123"})
        resp = ws.receive_json()
        assert resp["type"] == "pong"
        assert resp["trace_id"] == "test-123"
