"""Smoke tests for the FastAPI routes via TestClient."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ra3_inventory.api import create_app
from ra3_inventory.config import Config
from ra3_inventory.models import ProcessorInventory, Project, RadioRa3Processor
from ra3_inventory.storage.certs import store_pairing_to_disk
from ra3_inventory.storage.paths import ensure_profile_tree, profile_json_path
from ra3_inventory.storage.snapshots import write_snapshot


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


def test_profile_routes_reject_encoded_traversal(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    cfg = Config(session_token="test-token")
    client = TestClient(create_app(cfg))
    headers = {"X-RA3-Token": cfg.session_token}

    activated = client.post("/profiles/%2E%2E/activate", headers=headers)
    deleted = client.delete("/profiles/%2E%2E", headers=headers)

    assert activated.status_code == 400
    assert deleted.status_code == 400


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
    assert resp.json()[0]["credential_storage"] == "encrypted_disk"


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


def _snapshot(*, extracted_at: datetime, host: str) -> ProcessorInventory:
    return ProcessorInventory(
        extracted_at=extracted_at,
        source="fixture",
        host=host,
        duration_seconds=0,
        processor=RadioRa3Processor(
            href="/device/1",
            Name="Processor",
            DeviceType="RadioRa3Processor",
            SerialNumber="serial",
        ),
        project=Project(href="/project", Name="Project"),
    )


def test_sanitized_export_route_redacts_json(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    write_snapshot("abc", _snapshot(extracted_at=datetime.now(timezone.utc), host="10.0.0.1"))
    cfg = Config(active_profile_serial="abc", session_token="test-token")
    client = TestClient(create_app(cfg))

    resp = client.get("/export/json?sanitized=true", headers={"X-RA3-Token": cfg.session_token})

    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == 'attachment; filename="inventory-sanitized.json"'
    body = resp.json()
    assert body["host"] == "192.0.2.1"
    assert body["processor"]["SerialNumber"] is None


def test_snapshot_delete_and_prune_routes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    base = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
    first = write_snapshot("abc", _snapshot(extracted_at=base, host="first"))
    second = write_snapshot("abc", _snapshot(extracted_at=base.replace(minute=1), host="second"))
    third = write_snapshot("abc", _snapshot(extracted_at=base.replace(minute=2), host="third"))
    cfg = Config(active_profile_serial="abc", session_token="test-token")
    client = TestClient(create_app(cfg))
    headers = {"X-RA3-Token": cfg.session_token}

    protected = client.delete(f"/snapshots/{third.name}", headers=headers)
    deleted = client.delete(f"/snapshots/{first.name}", headers=headers)
    pruned = client.post("/snapshots/prune", headers=headers, json={"keep": 1})

    assert protected.status_code == 409
    assert deleted.status_code == 204
    assert pruned.status_code == 200
    assert pruned.json()["deleted"] == [second.name]
