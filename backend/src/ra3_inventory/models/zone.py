"""Zone model — a controllable load."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .base import HrefRef, RA3Resource


class ZoneCategory(BaseModel):
    """``Zone.Category`` — Type/SubType pair (e.g. ``Lighting/Dimmed``)."""

    model_config = ConfigDict(extra="allow")

    Type: str | None = None
    SubType: str | None = None
    IsLight: bool | None = None
    DeviceTypes: list[dict] | None = None


class Zone(RA3Resource):
    """``/zone/{id}`` — a single dimmer/switch/shade/fan load."""

    Name: str | None = None
    ControlType: str | None = None
    """e.g. ``Dimmed``, ``Switched``, ``Shade``, ``FanSpeed``."""

    Category: ZoneCategory | None = None
    Device: HrefRef | None = None
    AssociatedArea: HrefRef | None = None
    AssociatedFacade: HrefRef | None = None
    SortOrder: int | None = None
