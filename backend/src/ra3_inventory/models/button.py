"""Button, ButtonGroup, LED, and Engraving models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .base import HrefRef, RA3Resource


class ButtonEngraving(BaseModel):
    """``Button.Engraving`` — the printed/etched label on a keypad button.

    Named ``ButtonEngraving`` (not ``Engraving``) to avoid a name collision
    with the ``Engraving`` field on ``Button``: when ``from __future__ import
    annotations`` is on, the field default ``None`` shadows the class name
    in the class namespace before Pydantic resolves the forward reference.
    The exported alias ``Engraving = ButtonEngraving`` is kept for callers
    that import the historical name.
    """

    model_config = ConfigDict(extra="allow")

    Text: str | None = None
    Engravable: bool | None = None
    Glyph: str | None = None


# Backwards-friendly export alias for the historical class name.
Engraving = ButtonEngraving


class Button(RA3Resource):
    """``/button/{id}`` — a single keypad button or pico key."""

    Name: str | None = None
    ButtonNumber: int | None = None
    ButtonType: str | None = None
    """e.g. ``GeneralScene``, ``MultiTap``, ``Toggle``, ``Advanced``."""

    Engraving: ButtonEngraving | None = None
    Parent: HrefRef | None = None
    AssociatedLED: HrefRef | None = None
    ProgrammingModel: HrefRef | None = None


class ButtonGroup(RA3Resource):
    """``/buttongroup/{id}`` — a group of buttons on a keypad/pico."""

    Name: str | None = None
    ProgrammingType: str | None = None
    SortOrder: int | None = None
    Buttons: list[Button] | None = None
    """When fetched via ``/device/{id}/buttongroup/expanded``, this is
    populated inline with full Button objects; otherwise just HrefRefs."""

    Parent: HrefRef | None = None
    AffectedZones: list[HrefRef] | None = None
    StopIfMoving: bool | None = None


class Led(RA3Resource):
    """``/led/{id}`` — keypad LED indicator (one per button on Sunnata keypads)."""

    Name: str | None = None
    Parent: HrefRef | None = None
    AssociatedButton: HrefRef | None = None
    LEDLogic: str | None = None
