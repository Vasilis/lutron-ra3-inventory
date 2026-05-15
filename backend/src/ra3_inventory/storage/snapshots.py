"""Read/write ProcessorInventory snapshots to disk.

Snapshots are written under ``profiles/<serial>/snapshots/``, named by their
ISO8601 UTC timestamp. ``latest.json`` is a hardlink to the most recent file;
``baseline.json`` is a separately pinned hardlink for the M4 diff feature.

Snapshots are JSON-serialized via Pydantic v2's ``model_dump_json``. They
round-trip cleanly: ``ProcessorInventory.model_validate_json(...)``.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..models import ProcessorInventory
from .paths import (
    baseline_snapshot_path,
    ensure_profile_tree,
    latest_snapshot_path,
    snapshots_dir,
)

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class SnapshotSummary:
    """Lightweight metadata for the snapshots list endpoint."""

    filename: str
    extracted_at: datetime
    host: str
    is_latest: bool
    is_baseline: bool
    size_bytes: int


def _filename_for(snapshot: ProcessorInventory) -> str:
    iso = snapshot.extracted_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"{iso}.json"


def write_snapshot(serial: str, snapshot: ProcessorInventory) -> Path:
    """Write a snapshot, refresh the ``latest.json`` link, return its path."""
    ensure_profile_tree(serial)
    snap_dir = snapshots_dir(serial)
    out = snap_dir / _filename_for(snapshot)
    out.write_text(snapshot.model_dump_json(indent=2))

    # Refresh ``latest.json`` as a hardlink (atomic relink via rename).
    latest = latest_snapshot_path(serial)
    tmp = latest.with_suffix(".json.tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        os.link(out, tmp)
    except OSError:
        # Cross-filesystem or similar — fall back to copy.
        tmp.write_text(out.read_text())
    tmp.replace(latest)
    _LOG.info("Snapshot written: %s", out)
    return out


def read_snapshot(path: Path) -> ProcessorInventory:
    """Load a snapshot JSON into a ProcessorInventory."""
    return ProcessorInventory.model_validate_json(path.read_text())


def read_latest(serial: str) -> ProcessorInventory | None:
    """Return the most recent snapshot for a profile, or None if there isn't one."""
    p = latest_snapshot_path(serial)
    if not p.exists():
        return None
    return read_snapshot(p)


def read_baseline(serial: str) -> ProcessorInventory | None:
    """Return the user-pinned baseline snapshot for a profile, or None."""
    p = baseline_snapshot_path(serial)
    if not p.exists():
        return None
    return read_snapshot(p)


def set_baseline(serial: str, source_filename: str) -> Path:
    """Pin a specific snapshot as the M4 diff baseline."""
    src = snapshots_dir(serial) / source_filename
    if not src.exists():
        raise FileNotFoundError(f"Snapshot {source_filename} not found for profile {serial}")
    dst = baseline_snapshot_path(serial)
    tmp = dst.with_suffix(".json.tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        os.link(src, tmp)
    except OSError:
        tmp.write_text(src.read_text())
    tmp.replace(dst)
    return dst


def list_snapshots(serial: str) -> list[SnapshotSummary]:
    """Return summaries of every snapshot for a profile, newest first."""
    snap_dir = snapshots_dir(serial)
    if not snap_dir.exists():
        return []
    latest = latest_snapshot_path(serial).resolve() if latest_snapshot_path(serial).exists() else None
    baseline = baseline_snapshot_path(serial).resolve() if baseline_snapshot_path(serial).exists() else None

    out: list[SnapshotSummary] = []
    for p in snap_dir.iterdir():
        if not p.is_file() or not p.name.endswith(".json"):
            continue
        if p.name in ("latest.json", "baseline.json"):
            continue
        try:
            meta = json.loads(p.read_text())
            extracted_at = datetime.fromisoformat(meta.get("extracted_at", "").replace("Z", "+00:00"))
            host = meta.get("host", "")
        except Exception:  # noqa: BLE001
            continue
        out.append(
            SnapshotSummary(
                filename=p.name,
                extracted_at=extracted_at,
                host=host,
                is_latest=latest is not None and p.resolve() == latest,
                is_baseline=baseline is not None and p.resolve() == baseline,
                size_bytes=p.stat().st_size,
            )
        )
    out.sort(key=lambda s: s.extracted_at, reverse=True)
    return out
