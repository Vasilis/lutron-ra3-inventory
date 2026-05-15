"""Extraction routes — POST to start, SSE to follow progress."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from ...leap import AlreadyConnectedError, extract_inventory
from ...storage import materialize_pairing, write_snapshot
from ...storage.paths import profile_json_path
from ..deps import session_dependency
from ..dto import ExtractStartRequest, ExtractStartResponse
from ..events import sse_stream

router = APIRouter(prefix="/extract", tags=["extraction"], dependencies=[session_dependency])

_LOG = logging.getLogger(__name__)


@router.post("", response_model=ExtractStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def extract_start(body: ExtractStartRequest, request: Request) -> ExtractStartResponse:
    bus = request.app.state.event_bus
    channel = await bus.create("extract")
    asyncio.create_task(_run_extraction(request.app, channel.id, body))
    return ExtractStartResponse(extract_id=channel.id)


@router.get("/events")
async def extract_events(request: Request, extract_id: str) -> EventSourceResponse:
    bus = request.app.state.event_bus
    channel = await bus.get(extract_id)
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown extract_id {extract_id}")
    return EventSourceResponse(sse_stream(channel))


async def _run_extraction(app, channel_id: str, body: ExtractStartRequest) -> None:
    bus = app.state.event_bus
    channel = await bus.get(channel_id)
    assert channel is not None

    try:
        certs = materialize_pairing(body.profile_serial)
        if certs is None:
            raise RuntimeError(f"no pairing creds for profile {body.profile_serial}")

        meta_path = profile_json_path(body.profile_serial)
        host = "?"
        if meta_path.exists():
            host = json.loads(meta_path.read_text()).get("host", "?")
        if host == "?":
            raise RuntimeError(f"profile {body.profile_serial} has no host on record")

        await channel.publish({"phase": "connecting", "host": host})

        async def on_progress(event) -> None:
            await channel.publish({
                "phase": event.phase,
                "detail": event.detail,
                "progress": event.progress,
            })

        inventory = await extract_inventory(
            host=host,
            keyfile=certs.key,
            certfile=certs.cert,
            ca_certs=certs.ca,
            on_progress=on_progress,
            capture_raw=body.capture_raw,
        )

        snapshot_path = write_snapshot(body.profile_serial, inventory)

        # Refresh profile metadata
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        else:
            meta = {}
        meta["last_seen"] = datetime.now(timezone.utc).isoformat()
        if inventory.processor.FirmwareImage and inventory.processor.FirmwareImage.Firmware:
            meta["firmware"] = inventory.processor.FirmwareImage.Firmware.DisplayName or meta.get("firmware")
        meta_path.write_text(json.dumps(meta, indent=2))

        await channel.publish({
            "phase": "success",
            "detail": f"snapshot {snapshot_path.name}",
            "filename": snapshot_path.name,
            "device_count": len(inventory.devices),
            "area_count": len(inventory.areas),
            "duration_seconds": inventory.duration_seconds,
        })

    except AlreadyConnectedError as exc:
        await channel.publish({"phase": "error", "error": str(exc), "kind": "already_connected"})
    except Exception as exc:  # noqa: BLE001
        _LOG.exception("extraction failed for %s", body.profile_serial)
        await channel.publish({"phase": "error", "error": repr(exc)})
    finally:
        await asyncio.sleep(0.5)
        await bus.drop(channel_id)
