"""Inventory read endpoints — area tree, devices, zones, buttons."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ...models import (
    Area,
    Button,
    Device,
    ProcessorInventory,
    Zone,
)
from ..deps import LatestInventoryDep, session_dependency

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[session_dependency])


@router.get("", response_model=ProcessorInventory)
async def get_inventory(inv: LatestInventoryDep) -> ProcessorInventory:
    """Full current snapshot for the active profile."""
    return inv


@router.get("/areas", response_model=list[Area])
async def list_areas(inv: LatestInventoryDep) -> list[Area]:
    return inv.areas


@router.get("/devices", response_model=list[Device])
async def list_devices(inv: LatestInventoryDep, type: str | None = None) -> list[Device]:
    """All devices, optionally filtered by ``DeviceType``."""
    if type is None:
        return inv.devices
    return [d for d in inv.devices if d.DeviceType == type]


@router.get("/devices/{device_id}", response_model=Device)
async def get_device(inv: LatestInventoryDep, device_id: str) -> Device:
    """Look up a single device by its numeric id or full href."""
    target = device_id if device_id.startswith("/") else f"/device/{device_id}"
    for d in inv.devices:
        if d.href == target or d.href.endswith(f"/{device_id}"):
            return d
    if inv.processor.href == target:
        return inv.processor
    raise HTTPException(status.HTTP_404_NOT_FOUND, f"no device {device_id}")


@router.get("/zones", response_model=list[Zone])
async def list_zones(inv: LatestInventoryDep) -> list[Zone]:
    return inv.zones


@router.get("/buttons", response_model=list[Button])
async def list_buttons(inv: LatestInventoryDep, device: str | None = None) -> list[Button]:
    """Flat list of all buttons, optionally filtered to one device's expanded button groups."""
    if device is None:
        return inv.buttons
    target = device if device.startswith("/") else f"/device/{device}"
    out: list[Button] = []
    bgs = inv.button_group_expansions.get(target, [])
    for bg in bgs:
        if bg.Buttons:
            out.extend(bg.Buttons)
    return out
