"""Smoke tests for the FastAPI routes via TestClient."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ra3_inventory.api import create_app
from ra3_inventory.config import Config
from ra3_inventory.storage.certs import store_pairing_to_disk
from ra3_inventory.storage.paths import ensure_profile_tree, profile_json_path


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


def test_profiles_tolerate_bad_last_seen(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    ensure_profile_tree("abc")
    profile_json_path("abc").write_text(
        json.dumps(
            {
                "name": "Example",
                "host": "192.0.2.1",
                "last_seen": "not-a-date",
            }
        )
    )

    cfg = Config(session_token="test-token")
    client = TestClient(create_app(cfg))
    resp = client.get("/profiles", headers={"X-RA3-Token": cfg.session_token})

    assert resp.status_code == 200
    assert resp.json()[0]["last_seen"] is None


def test_deleting_active_profile_clears_config(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "ra3_inventory.api.routes.profiles.keychain.delete_pairing", lambda serial: None
    )
    ensure_profile_tree("abc")
    profile_json_path("abc").write_text(json.dumps({"name": "Example", "host": "192.0.2.1"}))

    cfg = Config(active_profile_serial="abc", session_token="test-token")
    client = TestClient(create_app(cfg))
    resp = client.delete("/profiles/abc", headers={"X-RA3-Token": cfg.session_token})

    assert resp.status_code == 204
    assert cfg.active_profile_serial is None
    assert json.loads((tmp_path / "config.json").read_text())["active_profile_serial"] is None


def test_profiles_report_encrypted_disk_credentials(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("ra3_inventory.api.routes.profiles.keychain.is_available", lambda: False)
    ensure_profile_tree("abc")
    profile_json_path("abc").write_text(json.dumps({"name": "Example", "host": "192.0.2.1"}))
    store_pairing_to_disk("abc", key_pem="KEY", cert_pem="CERT", ca_pem="CA", passphrase="pw")

    cfg = Config(session_token="test-token")
    client = TestClient(create_app(cfg))
    resp = client.get("/profiles", headers={"X-RA3-Token": cfg.session_token})

    assert resp.status_code == 200
    assert resp.json()[0]["has_certs"] is True


def test_snapshot_routes_reject_reserved_or_traversal_names(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    cfg = Config(active_profile_serial="abc", session_token="test-token")
    client = TestClient(create_app(cfg))

    reserved = client.get("/snapshots/baseline.json", headers={"X-RA3-Token": cfg.session_token})
    traversal = client.post(
        "/snapshots/baseline",
        headers={"X-RA3-Token": cfg.session_token},
        json={"filename": "../profile.json"},
    )

    assert reserved.status_code == 400
    assert traversal.status_code == 400
