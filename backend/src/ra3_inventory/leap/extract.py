"""Raw-LEAP inventory extractor — typed Pydantic output.

Ported from ``docs/legacy/lutron_raw_extract.py`` (the canonical standalone
extractor) to drive our vendored ``LeapProtocol`` directly and emit
``ProcessorInventory`` (Pydantic v2) instead of an untyped dict.

Endpoints walked (RA 3 path):
- ``/project``, ``/server``, ``/server/1``, ``/server/1/status/ping``
- ``/area``, ``/zone``, ``/controlstation``
- ``/device?where=IsThisDevice:true`` (the processor)
- ``/device?where=IsThisDevice:false`` (everything else)
- ``/buttongroup``, ``/button``, ``/led``
- ``/virtualbutton``, ``/areascene``, ``/occupancygroup``
- ``/project/timeclockeventrules``
- For every keypad-like device: ``/device/{id}/buttongroup/expanded``
- For every ProgrammingModel referenced from those buttons: ``/programmingmodel/{id}``
- For every Preset referenced from those models: ``/preset/{id}``

The result is a typed ``ProcessorInventory`` with all cross-references
preserved as ``HrefRef``s. The UI resolves them on render via flat
href-keyed maps the extractor builds during indexing.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable, Iterable
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from ..models import (
    Area,
    AreaScene,
    Button,
    ButtonGroup,
    ControlStation,
    Device,
    ExtractionEvent,
    Led,
    Preset,
    ProcessorInventory,
    ProgrammingModel,
    Project,
    RadioRa3Processor,
    Server,
    TimeclockEventRule,
    VirtualButton,
    Zone,
    parse_device,
)
from .errors import BridgeDisconnectedError
from .messages import Response
from .protocol import LeapProtocol

_LOG = logging.getLogger(__name__)

ProgressFn = Callable[[ExtractionEvent], None] | Callable[[ExtractionEvent], Awaitable[None]] | None

TOPLEVEL_ENDPOINTS: tuple[str, ...] = (
    "/project",
    "/server",
    "/server/1",
    "/server/1/status/ping",
    "/server/2/id",  # secondary processor (404 on single-proc RA 3 is fine)
    "/area",
    "/area/status",
    "/zone",
    "/controlstation",
    "/buttongroup",
    "/button",
    "/led",
    "/virtualbutton",
    "/areascene",
    "/occupancygroup",
    "/project/timeclockeventrules",
    "/system/away/1/status",
    "/curve/1",
)

# Bare /device returns 204 on RA 3; the where-filtered queries are required.
DEVICE_ENDPOINTS: tuple[str, ...] = (
    "/device?where=IsThisDevice:true",
    "/device?where=IsThisDevice:false",
)

# DeviceTypes that carry button groups. On older RA 3 firmware each device
# also exposed a top-level ``ButtonGroups: [{"href": "..."}, ...]`` field, but
# newer firmware (26.03.12f000+) drops it — keypads are detected by
# DeviceType instead. We still keep the field-based detection as an OR
# fallback for older firmwares.
KEYPAD_DEVICE_TYPES: frozenset[str] = frozenset(
    {
        "SunnataKeypad",
        "SunnataHybridKeypad",
        "SeeTouchKeypad",
        "SeeTouchHybridKeypad",
        "SeeTouchTabletopKeypad",
        "SeeTouchInternational",
        "GrafikTHybridKeypad",
        "HomeownerKeypad",
        "AlisseKeypad",
        "PalladiomKeypad",
        "PhantomKeypad",
        "Pico1Button",
        "Pico2Button",
        "Pico2ButtonRaiseLower",
        "Pico3Button",
        "Pico3ButtonRaiseLower",
        "Pico4Button",
        "Pico4ButtonScene",
        "Pico4ButtonZone",
        "Pico4Button2Group",
        "PaddleSwitchPico",
        "FourGroupRemote",
        "CasetaFourGroupRemote",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_from_body(body: Any) -> list:
    """LEAP wraps collections as ``{'Devices': [...]}`` etc. Find the list."""
    if isinstance(body, list):
        return body
    if not isinstance(body, dict):
        return []
    for v in body.values():
        if isinstance(v, list):
            return v
    return []


def _first_obj_from_body(body: Any) -> dict | None:
    """For ``OneXxxDefinition`` responses, return the inner dict."""
    if not isinstance(body, dict):
        return None
    for v in body.values():
        if isinstance(v, dict):
            return v
    return body


def _walk_hrefs(obj: object) -> Iterable[str]:
    """Yield every string value found under a ``href`` key, recursively."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "href" and isinstance(v, str):
                yield v
            else:
                yield from _walk_hrefs(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_hrefs(item)


def _raw_response_repr(resp: Response | None) -> dict:
    """Convert a Response NamedTuple to a JSON-safe dict for the raw echo."""
    if resp is None:
        return {"status": None, "body": None, "error": "no response"}
    status = resp.Header.StatusCode
    return {
        "status": status.code if status is not None else None,
        "status_message": status.message if status is not None else None,
        "communique_type": resp.CommuniqueType,
        "body": resp.Body,
    }


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class InventoryExtractor:
    """Drives the full graph walk against a connected ``LeapProtocol``.

    Single-use: instantiate, ``await run()``, then discard. Not reusable
    across multiple extractions — the processor only allows one LEAP
    connection at a time anyway, so the connect-extract-disconnect cycle
    is the natural unit.
    """

    def __init__(
        self,
        proto: LeapProtocol,
        host: str,
        on_progress: ProgressFn = None,
        capture_raw: bool = False,
    ) -> None:
        self._proto = proto
        self._host = host
        self._on_progress = on_progress
        self._capture_raw = capture_raw
        self._raw: dict[str, dict] = {}
        self._proto_task: asyncio.Task | None = None

    # -- progress -----------------------------------------------------------

    async def _emit(
        self,
        phase: str,
        detail: str,
        progress: float | None = None,
        error: str | None = None,
    ) -> None:
        if self._on_progress is None:
            return
        event = ExtractionEvent(phase=phase, detail=detail, progress=progress, error=error)  # type: ignore[arg-type]
        result = self._on_progress(event)
        if asyncio.iscoroutine(result):
            await result

    # -- protocol IO --------------------------------------------------------

    async def _read(self, url: str) -> dict | None:
        """Send a LEAP ReadRequest, return the parsed Body, capture raw if requested."""
        try:
            resp = await self._proto.request("ReadRequest", url)
        except BridgeDisconnectedError:
            _LOG.warning("LEAP bridge disconnected during %s", url)
            if self._capture_raw:
                self._raw[url] = {"status": None, "body": None, "error": "disconnected"}
            return None
        except Exception as exc:
            _LOG.warning("Error reading %s: %r", url, exc)
            if self._capture_raw:
                self._raw[url] = {"status": None, "body": None, "error": repr(exc)}
            return None

        if self._capture_raw:
            self._raw[url] = _raw_response_repr(resp)

        status = resp.Header.StatusCode
        if status is None or not status.is_successful():
            _LOG.debug("Non-success status for %s: %s", url, status)
            return None
        return resp.Body

    # -- main flow ----------------------------------------------------------

    async def run(self) -> ProcessorInventory:
        """Walk the full graph and return a typed ProcessorInventory."""
        started = datetime.now(timezone.utc)
        t0 = asyncio.get_running_loop().time()

        # Start the protocol's read loop on a background task.
        self._proto_task = asyncio.create_task(self._proto.run(), name="leap-protocol-run")
        try:
            await self._emit("toplevel", "Reading top-level endpoints", progress=0.05)
            toplevel = await self._fetch_toplevel()

            await self._emit("devices", "Reading device list", progress=0.15)
            processor, devices = await self._fetch_devices()

            # Walk per-zone refs if the bulk /zone read came back empty
            # (newer RA 3 firmware doesn't support the bulk endpoint).
            bulk_zones = [
                Zone.model_validate(z)
                for z in _list_from_body(toplevel.get("/zone"))
                if isinstance(z, dict)
            ]
            if bulk_zones:
                resolved_zones = bulk_zones
            else:
                await self._emit("zones", "Walking LocalZones references", progress=0.22)
                resolved_zones = await self._fetch_zones_by_reference(devices)

            await self._emit("buttongroup_expanded", "Expanding keypad button groups", progress=0.3)
            bg_expansions = await self._fetch_expanded_buttongroups(devices)

            await self._emit("programming_models", "Resolving programming models", progress=0.55)
            programming_models = await self._fetch_programming_models(bg_expansions)

            await self._emit("presets", "Resolving presets", progress=0.8)
            presets = await self._fetch_presets(programming_models.values())

            ending_project = _first_obj_from_body(await self._read("/project"))
            starting_project = _first_obj_from_body(toplevel.get("/project"))
            partial = bool(
                starting_project
                and ending_project
                and starting_project.get("ProjectModifiedTimestamp")
                != ending_project.get("ProjectModifiedTimestamp")
            )

            await self._emit("indexing", "Building typed inventory", progress=0.95)
            inventory = self._build_inventory(
                started=started,
                duration=asyncio.get_running_loop().time() - t0,
                toplevel=toplevel,
                processor=processor,
                devices=devices,
                resolved_zones=resolved_zones,
                bg_expansions=bg_expansions,
                programming_models=programming_models,
                presets=presets,
                partial=partial,
            )

            await self._emit("done", "Extraction complete", progress=1.0)
            return inventory
        finally:
            if self._proto_task is not None and not self._proto_task.done():
                self._proto_task.cancel()
                with suppress(asyncio.CancelledError, Exception):
                    await self._proto_task

    # -- phases -------------------------------------------------------------

    async def _fetch_toplevel(self) -> dict[str, dict | None]:
        out: dict[str, dict | None] = {}
        for url in TOPLEVEL_ENDPOINTS:
            out[url] = await self._read(url)
        return out

    async def _fetch_devices(self) -> tuple[RadioRa3Processor, list[Device]]:
        proc_body = await self._read("/device?where=IsThisDevice:true")
        other_body = await self._read("/device?where=IsThisDevice:false")

        # Capture raw echoes under the explicit DEVICE_ENDPOINT keys too,
        # so downstream code can rely on either naming.
        if self._capture_raw:
            self._raw.setdefault(
                "/device?where=IsThisDevice:true",
                self._raw.get("/device?where=IsThisDevice:true", {}),
            )

        proc_list = _list_from_body(proc_body)
        if not proc_list or not isinstance(proc_list[0], dict):
            raise RuntimeError(
                "Processor self-query returned no devices — "
                "expected exactly one entry from /device?where=IsThisDevice:true"
            )
        processor = parse_device(proc_list[0])
        if not isinstance(processor, RadioRa3Processor):
            # Fallback to the base RadioRa3Processor shape — the registry
            # may have mapped an unknown variant.
            processor = RadioRa3Processor.model_validate(proc_list[0])

        devices: list[Device] = []
        for d_raw in _list_from_body(other_body):
            if isinstance(d_raw, dict):
                devices.append(parse_device(d_raw))
        return processor, devices

    async def _fetch_expanded_buttongroups(
        self, devices: Iterable[Device]
    ) -> dict[str, list[ButtonGroup]]:
        out: dict[str, list[ButtonGroup]] = {}
        # Newer RA 3 firmware (26.03.12+) drops the per-device ButtonGroups
        # field, so detect keypad-likes by DeviceType too. Either signal
        # qualifies a device.
        targets = [d for d in devices if d.ButtonGroups or d.DeviceType in KEYPAD_DEVICE_TYPES]
        total = len(targets)
        for i, d in enumerate(targets, start=1):
            url = f"{d.href}/buttongroup/expanded"
            body = await self._read(url)
            bgs: list[ButtonGroup] = []
            for raw in _list_from_body(body):
                if isinstance(raw, dict):
                    bgs.append(ButtonGroup.model_validate(raw))
            out[d.href] = bgs
            if total:
                await self._emit(
                    "buttongroup_expanded",
                    f"{i} of {total} keypads",
                    progress=0.3 + 0.25 * (i / total),
                )
        return out

    async def _fetch_programming_models(
        self, bg_expansions: dict[str, list[ButtonGroup]]
    ) -> dict[str, ProgrammingModel]:
        pm_hrefs: set[str] = set()
        for bgs in bg_expansions.values():
            for bg in bgs:
                for btn in bg.Buttons or []:
                    if btn.ProgrammingModel is not None and btn.ProgrammingModel.href:
                        pm_hrefs.add(btn.ProgrammingModel.href)

        out: dict[str, ProgrammingModel] = {}
        total = len(pm_hrefs)
        for i, href in enumerate(sorted(pm_hrefs), start=1):
            body = await self._read(href)
            obj = _first_obj_from_body(body)
            if isinstance(obj, dict):
                out[href] = ProgrammingModel.model_validate(obj)
            if total:
                await self._emit(
                    "programming_models",
                    f"{i} of {total} programming models",
                    progress=0.55 + 0.25 * (i / total),
                )
        return out

    async def _fetch_zones_by_reference(self, devices: Iterable[Device]) -> list[Zone]:
        """Fallback when bare ``/zone`` returns ``not supported`` on newer firmware.

        Walks every ``LocalZones[].href`` across all devices, fetches each
        ``/zone/{id}`` individually, and returns the union.
        """
        hrefs: set[str] = set()
        for d in devices:
            for ref in d.LocalZones:
                if ref.href:
                    hrefs.add(ref.href)

        out: list[Zone] = []
        total = len(hrefs)
        for i, href in enumerate(sorted(hrefs), start=1):
            body = await self._read(href)
            obj = _first_obj_from_body(body)
            if isinstance(obj, dict):
                out.append(Zone.model_validate(obj))
            if total:
                await self._emit(
                    "zones",
                    f"{i} of {total} zones",
                    progress=0.22 + 0.06 * (i / total),
                )
        return out

    async def _fetch_presets(
        self, programming_models: Iterable[ProgrammingModel]
    ) -> dict[str, Preset]:
        # Schema variants we've seen in the wild:
        #   - Legacy:  *OnPresetAssignments[] -> {href: /preset/N}
        #   - Newer:   AdvancedToggleProperties.{Primary,Secondary}Preset.href
        #              SingleActionProgrammingModel.Preset.href
        #              SingleScene{Raise,Lower}ProgrammingModel.Preset.href
        # Rather than enumerate them, walk every PM dict tree and collect any
        # value that looks like a ``/preset/...`` href. Robust to future
        # additions.
        preset_hrefs: set[str] = set()
        for pm in programming_models:
            for ref in _walk_hrefs(pm.model_dump(by_alias=True)):
                if ref.startswith("/preset/"):
                    preset_hrefs.add(ref)

        out: dict[str, Preset] = {}
        total = len(preset_hrefs)
        for i, href in enumerate(sorted(preset_hrefs), start=1):
            body = await self._read(href)
            obj = _first_obj_from_body(body)
            if isinstance(obj, dict):
                out[href] = Preset.model_validate(obj)
            if total:
                await self._emit(
                    "presets",
                    f"{i} of {total} presets",
                    progress=0.8 + 0.15 * (i / total),
                )
        return out

    # -- assembly -----------------------------------------------------------

    def _build_inventory(
        self,
        *,
        started: datetime,
        duration: float,
        toplevel: dict[str, dict | None],
        processor: RadioRa3Processor,
        devices: list[Device],
        resolved_zones: list[Zone],
        bg_expansions: dict[str, list[ButtonGroup]],
        programming_models: dict[str, ProgrammingModel],
        presets: dict[str, Preset],
        partial: bool,
    ) -> ProcessorInventory:
        project_obj = _first_obj_from_body(toplevel.get("/project")) or {}
        server_obj = _first_obj_from_body(toplevel.get("/server/1"))

        return ProcessorInventory(
            extracted_at=started,
            source="live",
            host=self._host,
            duration_seconds=duration,
            partial=partial,
            processor=processor,
            project=Project.model_validate(project_obj),
            server=Server.model_validate(server_obj) if server_obj else None,
            areas=[
                Area.model_validate(a)
                for a in _list_from_body(toplevel.get("/area"))
                if isinstance(a, dict)
            ],
            devices=devices,
            zones=resolved_zones,
            buttons=[
                Button.model_validate(b)
                for b in _list_from_body(toplevel.get("/button"))
                if isinstance(b, dict)
            ],
            button_groups=[
                ButtonGroup.model_validate(bg)
                for bg in _list_from_body(toplevel.get("/buttongroup"))
                if isinstance(bg, dict)
            ],
            leds=[
                Led.model_validate(led)
                for led in _list_from_body(toplevel.get("/led"))
                if isinstance(led, dict)
            ],
            control_stations=[
                ControlStation.model_validate(cs)
                for cs in _list_from_body(toplevel.get("/controlstation"))
                if isinstance(cs, dict)
            ],
            area_scenes=[
                AreaScene.model_validate(s)
                for s in _list_from_body(toplevel.get("/areascene"))
                if isinstance(s, dict)
            ],
            virtual_buttons=[
                VirtualButton.model_validate(v)
                for v in _list_from_body(toplevel.get("/virtualbutton"))
                if isinstance(v, dict)
            ],
            timeclock_event_rules=[
                TimeclockEventRule.model_validate(t)
                for t in _list_from_body(toplevel.get("/project/timeclockeventrules"))
                if isinstance(t, dict)
            ],
            button_group_expansions=bg_expansions,
            programming_models=programming_models,
            presets=presets,
            raw_responses=self._raw if self._capture_raw else None,
        )
