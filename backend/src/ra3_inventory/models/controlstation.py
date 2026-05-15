"""ControlStation — the physical wallplate gang holding one or more keypad devices."""

from __future__ import annotations

from .base import HrefRef, RA3Resource


class ControlStation(RA3Resource):
    """``/controlstation/{id}`` — a wallplate location with ganged devices."""

    Name: str | None = None
    SortOrder: int | None = None
    AssociatedArea: HrefRef | None = None
    AssociatedGangedDevices: list[HrefRef] | None = None
