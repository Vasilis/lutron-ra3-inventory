"""Smoke tests for the FastAPI routes via TestClient."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ra3_inventory.api import create_app
from ra3_inventory.config import Config


@pytest.fixture
def app_and_token():
    cfg = Config()
    cfg.session_token = "test-token"
    app = create_app(cfg)
    return app, cfg.session_token


def test_health_no_auth(app_and_token) -> None:
    """``/health`` should answer without the session token (so the webview can probe)."""
    app, _ = app_and_token
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_version_no_auth(app_and_token) -> None:
    app, _ = app_and_token
    client = TestClient(app)
    resp = client.get("/version")
    assert resp.status_code == 200
    assert resp.json()["schema_version"] == 1


def test_protected_endpoint_rejects_without_token(app_and_token) -> None:
    """``/profiles`` requires the session token."""
    app, _ = app_and_token
    client = TestClient(app)
    resp = client.get("/profiles")
    assert resp.status_code == 401


def test_protected_endpoint_accepts_with_token(app_and_token) -> None:
    app, token = app_and_token
    client = TestClient(app)
    resp = client.get("/profiles", headers={"X-RA3-Token": token})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_inventory_404_without_snapshot(app_and_token) -> None:
    """No active profile → ``/inventory`` returns 404 with the expected message."""
    app, token = app_and_token
    client = TestClient(app)
    resp = client.get("/inventory", headers={"X-RA3-Token": token})
    assert resp.status_code == 404
    assert "active profile" in resp.json()["detail"]
