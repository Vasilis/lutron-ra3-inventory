"""Scenes, virtual buttons, and timeclock event rules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .base import HrefRef, RA3Resource


class AreaScene(RA3Resource):
    """``/areascene/{id}`` — RA 3 per-area named scene (replaces Caseta ``/scene``)."""

    Name: str | None = None
    Parent: HrefRef | None = None
    ProgrammingModel: HrefRef | None = None
    SortOrder: int | None = None


class VirtualButton(RA3Resource):
    """``/virtualbutton/{id}`` — timeclock target / scene trigger (RA 3)."""

    Name: str | None = None
    Category: dict | None = None
    ProgrammingModel: HrefRef | None = None
    IsProgrammed: bool | None = None
    Parent: HrefRef | None = None


class TimeReference(BaseModel):
    """Trigger time spec — clock-based or sunrise/sunset-relative."""

    model_config = ConfigDict(extra="allow")

    Time: str | None = None
    EventName: str | None = None
    """e.g. ``Sunrise``, ``Sunset``, ``CivilDusk``."""

    Offset: int | None = None


class TimeclockEventRule(RA3Resource):
    """``/project/timeclockeventrules`` entry."""

    Name: str | None = None
    Enabled: bool | None = None
    DaysOfWeek: list[str] | str | None = None
    TimeReference: TimeReference | str | None = None
    Actions: list[dict] | None = None
    Parent: HrefRef | None = None
