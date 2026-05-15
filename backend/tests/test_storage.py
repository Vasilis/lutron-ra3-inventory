"""Regression tests for credential materialization and snapshot durability."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from ra3_inventory.models import ProcessorInventory, Project, RadioRa3Processor
from ra3_inventory.storage import keychain
from ra3_inventory.storage.certs import (
    has_encrypted_pairing,
    has_plain_pairing,
    materialize_pairing,
    store_pairing_to_disk,
)
from ra3_inventory.storage.paths import certs_dir
from ra3_inventory.storage.snapshots import (
    list_snapshots,
    read_baseline,
    set_baseline,
    write_snapshot,
)


def _inventory(*, extracted_at: datetime, host: str) -> ProcessorInventory:
    return ProcessorInventory(
        extracted_at=extracted_at,
        source="fixture",
        host=host,
        duration_seconds=0,
        processor=RadioRa3Processor(href="/device/1", DeviceType="RadioRa3Processor"),
        project=Project(href="/project"),
    )


def test_keychain_materialization_uses_temp_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(keychain, "is_available", lambda: True)
    monkeypatch.setattr(keychain, "load_pairing", lambda serial: ("KEY", "CERT", "CA"))

    paths = materialize_pairing("abc")

    assert paths is not None
    assert paths.temp_dir is not None
    assert paths.key.read_text() == "KEY"
    assert not certs_dir("abc").exists()

    temp_dir = paths.temp_dir
    paths.cleanup()
    assert not temp_dir.exists()


def test_same_timestamp_snapshots_do_not_overwrite(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    timestamp = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)

    first = write_snapshot("abc", _inventory(extracted_at=timestamp, host="first"))
    set_baseline("abc", first.name)
    second = write_snapshot("abc", _inventory(extracted_at=timestamp, host="second"))

    assert first != second
    assert first.exists()
    assert second.exists()
    assert read_baseline("abc") is not None
    assert read_baseline("abc").host == "first"  # type: ignore[union-attr]

    snapshots = list_snapshots("abc")
    assert {s.filename for s in snapshots} == {first.name, second.name}
    assert sum(s.is_latest for s in snapshots) == 1
    assert sum(s.is_baseline for s in snapshots) == 1


def test_encrypted_disk_pairing_never_leaves_plaintext(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr(keychain, "is_available", lambda: False)

    store_pairing_to_disk("abc", key_pem="KEY", cert_pem="CERT", ca_pem="CA", passphrase="secret")

    assert has_encrypted_pairing("abc")
    assert not has_plain_pairing("abc")

    paths = materialize_pairing("abc", passphrase="secret")
    assert paths is not None
    assert paths.temp_dir is not None
    assert paths.key.read_text() == "KEY"
    assert not has_plain_pairing("abc")

    temp_dir = paths.temp_dir
    paths.cleanup()
    assert not temp_dir.exists()


def test_snapshot_filename_validation_blocks_traversal(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)

    for filename in (
        "../profile.json",
        "nested/snapshot.json",
        r"nested\snapshot.json",
        "latest.json",
    ):
        try:
            set_baseline("abc", filename)
        except ValueError:
            continue
        raise AssertionError(f"expected {filename!r} to be rejected")
