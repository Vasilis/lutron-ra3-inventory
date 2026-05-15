"""Snapshot list / read / baseline-pin routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ...models import ProcessorInventory
from ...storage import list_snapshots, read_snapshot, set_baseline, snapshot_path
from ..deps import ActiveSerialDep, session_dependency
from ..dto import SetBaselineRequest, SnapshotEntry

router = APIRouter(prefix="/snapshots", tags=["snapshots"], dependencies=[session_dependency])


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
    try:
        p = snapshot_path(serial, filename)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if not p.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no snapshot {filename}")
    return read_snapshot(p)


@router.post("/baseline", status_code=status.HTTP_204_NO_CONTENT)
async def pin_baseline(serial: ActiveSerialDep, body: SetBaselineRequest) -> None:
    try:
        set_baseline(serial, body.filename)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
