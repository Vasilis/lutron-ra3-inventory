"""Pairing routes — POST to start, SSE to follow the button-press dance."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from contextlib import suppress
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from ...leap import async_pair, connect_leap
from ...models import RadioRa3Processor, parse_device
from ...storage import keychain
from ...storage.certs import store_pairing_to_disk
from ...storage.paths import (
    ensure_profile_tree,
    profile_json_path,
)
from ..deps import session_dependency
from ..dto import PairStartRequest, PairStartResponse
from ..events import sse_stream

router = APIRouter(prefix="/pair", tags=["pairing"], dependencies=[session_dependency])

_LOG = logging.getLogger(__name__)


@router.post("/start", response_model=PairStartResponse, status_code=status.HTTP_202_ACCEPTED)
async def pair_start(body: PairStartRequest, request: Request) -> PairStartResponse:
    bus = request.app.state.event_bus
    channel = await bus.create("pair")
    bus.start_task(
        _run_pairing(request.app, channel.id, body),
        name=f"pairing-{channel.id}",
    )
    return PairStartResponse(pair_id=channel.id)


@router.get("/events")
async def pair_events(request: Request, pair_id: str) -> EventSourceResponse:
    bus = request.app.state.event_bus
    channel = await bus.get(pair_id)
    if channel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown pair_id {pair_id}")
    return EventSourceResponse(sse_stream(channel))


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


async def _run_pairing(app, channel_id: str, body: PairStartRequest) -> None:
    bus = app.state.event_bus
    cfg = app.state.config
    channel = await bus.get(channel_id)
    assert channel is not None

    try:
        keychain_available = keychain.is_available()
        if not keychain_available and body.disk_passphrase is None:
            raise RuntimeError(
                "macOS Keychain unavailable — provide disk_passphrase "
                "to use encrypted on-disk credential storage"
            )

        await channel.publish({"phase": "starting", "host": body.host})

        ready_fired = asyncio.Event()

        def _ready_cb() -> None:
            ready_fired.set()

        # async_pair will fire ready_cb after the TLS handshake but before the
        # button-press wait. Bridge that into an SSE event.
        async def _watch_ready() -> None:
            await ready_fired.wait()
            await channel.publish(
                {
                    "phase": "ready",
                    "detail": "Press the pairing button on your Lutron processor (within 30 seconds).",
                }
            )

        watcher = asyncio.create_task(_watch_ready())
        try:
            pairing_data = await async_pair(body.host, ready=_ready_cb)
        finally:
            watcher.cancel()
            with suppress(asyncio.CancelledError):
                await watcher

        # We have key + cert + ca PEMs. Open a single TLS query to /device?where=
        # IsThisDevice:true to recover the processor SerialNumber, which becomes
        # the profile directory key.
        with (
            tempfile.NamedTemporaryFile("w", suffix=".key", delete=False) as kf,
            tempfile.NamedTemporaryFile("w", suffix=".crt", delete=False) as cf,
            tempfile.NamedTemporaryFile("w", suffix=".ca", delete=False) as af,
        ):
            kf.write(pairing_data["key"])
            cf.write(pairing_data["cert"])
            af.write(pairing_data["ca"])
            kf.flush()
            cf.flush()
            af.flush()
            kfp, cfp, afp = kf.name, cf.name, af.name

        await channel.publish({"phase": "discovering", "detail": "Reading processor info..."})

        try:
            proto = await connect_leap(body.host, keyfile=kfp, certfile=cfp, ca_certs=afp)
            proto_task = asyncio.create_task(proto.run())
            try:
                resp = await proto.request("ReadRequest", "/device?where=IsThisDevice:true")
                if resp.Body is None:
                    raise RuntimeError("processor returned no body for self-query")
                # Body is { "Devices": [ {...} ] } or { "Device": {...} }
                devs = next((v for v in resp.Body.values() if isinstance(v, list)), [])
                if not devs:
                    raise RuntimeError("processor returned no devices in self-query")
                processor = parse_device(devs[0])
            finally:
                proto.close()
                await proto.wait_closed()
                proto_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await proto_task
        finally:
            for path in (kfp, cfp, afp):
                with suppress(OSError):
                    os.unlink(path)

        serial = str(processor.SerialNumber or "unknown")
        if (
            serial == "unknown"
            and isinstance(processor, RadioRa3Processor)
            and processor.NetworkInterfaces
        ):
            # Some Sunnata firmwares omit SerialNumber on the processor; fall
            # back to the MAC address.
            mac = processor.NetworkInterfaces[0].MACAddress or ""
            if mac:
                serial = mac.replace(":", "").lower()
        if not serial or serial == "unknown":
            raise RuntimeError("could not derive a stable profile key from processor")

        ensure_profile_tree(serial)
        if keychain_available:
            keychain.store_pairing(
                serial,
                key_pem=pairing_data["key"],
                cert_pem=pairing_data["cert"],
                ca_pem=pairing_data["ca"],
            )
        else:
            store_pairing_to_disk(
                serial,
                key_pem=pairing_data["key"],
                cert_pem=pairing_data["cert"],
                ca_pem=pairing_data["ca"],
                passphrase=body.disk_passphrase,
            )

        fw = processor.firmware_display_name or ""

        profile_json_path(serial).write_text(
            json.dumps(
                {
                    "name": body.name,
                    "host": body.host,
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                    "firmware": fw,
                    "leap_version": pairing_data["version"],
                },
                indent=2,
            )
        )

        cfg.active_profile_serial = serial
        cfg.save()

        await channel.publish(
            {
                "phase": "success",
                "serial": serial,
                "name": body.name,
                "host": body.host,
                "firmware": fw,
            }
        )
    except asyncio.TimeoutError:
        await channel.publish({"phase": "timeout", "detail": "button press window expired"})
    except Exception as exc:
        _LOG.exception("pairing failed for %s", body.host)
        await channel.publish({"phase": "error", "error": repr(exc)})
    finally:
        await bus.finish(channel_id)
