"""Snapshot list / read / baseline-pin routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ...models import ProcessorInventory
from ...storage import list_snapshots, read_snapshot, set_baseline
from ...storage.paths import snapshots_dir
from ..deps import ActiveSerialDep, SessionDep
from ..dto import SetBaselineRequest, SnapshotEntry

router = APIRouter(prefix="/snapshots", tags=["snapshots"], dependencies=[SessionDep])


@router.get("", response_model=list[SnapshotEntry])
async def list_(serial: ActiveSerialDep) -> list[SnapshotEntry]:
    summaries = list_snapshots(serial)
    return [
        SnapshotEntry(
            filename=s.filename,
            extracted_at=s.extracted_at,
            host=s.host,
            is_latest=s.is_latest,
            is_baseline=s.is_baseline,
            size_bytes=s.size_bytes,
        )
        for s in summaries
    ]


@router.get("/{filename}", response_model=ProcessorInventory)
async def get_one(serial: ActiveSerialDep, filename: str) -> ProcessorInventory:
    p = snapshots_dir(serial) / filename
    if not p.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no snapshot {filename}")
    return read_snapshot(p)


@router.post("/baseline", status_code=status.HTTP_204_NO_CONTENT)
async def pin_baseline(serial: ActiveSerialDep, body: SetBaselineRequest) -> None:
    try:
        set_baseline(serial, body.filename)
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
