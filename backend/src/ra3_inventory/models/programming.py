"""ProgrammingModel + Preset graph — what a button actually does.

The chain is:
  Button.ProgrammingModel.href
    → ProgrammingModel.{Press,Release,DoubleTap,Hold}OnPresetAssignments[].href
      → Preset.{DimmedLevel,FanSpeed,Tilt,SwitchedLevel}Assignments[]
          → ``AssignableObject.href`` (a Zone) + a Level value

The ported extractor walks this graph once and the snapshot stores all three
levels (ProgrammingModel + Preset + Assignment) as flat top-level dicts keyed
by href.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .base import HrefRef, RA3Resource


class Assignment(BaseModel):
    """One step within a Preset — assign a Zone to a target Level/Speed/Tilt."""

    model_config = ConfigDict(extra="allow")

    AssignableObject: HrefRef | None = None
    """Usually a Zone href. Can also be an AreaScene or VirtualButton."""

    Level: float | int | None = None
    FanSpeed: str | None = None
    Tilt: float | int | None = None
    SwitchedLevel: str | None = None
    """``On`` or ``Off`` for switched loads."""

    RampRate: dict | None = None
    DelayTime: dict | None = None


class Preset(RA3Resource):
    """``/preset/{id}`` — a named target state for a button/scene to fire."""

    Name: str | None = None
    DimmedLevelAssignments: list[Assignment] | None = None
    SwitchedLevelAssignments: list[Assignment] | None = None
    FanSpeedAssignments: list[Assignment] | None = None
    TiltAssignments: list[Assignment] | None = None
    SceneAssignments: list[Assignment] | None = None
    ParentLink: HrefRef | None = None


class ProgrammingModel(RA3Resource):
    """``/programmingmodel/{id}`` — what happens on press/release/etc."""

    Name: str | None = None
    ProgrammingModelType: str | None = None
    """e.g. ``SimpleConditional``, ``Advanced``, ``RaiseLower``, ``MultiTap``."""

    PressOnPresetAssignments: list[HrefRef] | None = None
    ReleaseOnPresetAssignments: list[HrefRef] | None = None
    DoubleTapOnPresetAssignments: list[HrefRef] | None = None
    HoldOnPresetAssignments: list[HrefRef] | None = None
    Parent: HrefRef | None = None
