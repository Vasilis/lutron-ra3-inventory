"""The ProcessorInventory v1 snapshot envelope and extraction-progress events.

A ProcessorInventory is the canonical, typed view of one full LEAP extraction.
It's what's written to disk, served by the API, and rendered by the UI. The
schema is versioned via ``schema_version``; v2 will be introduced only when
fields change shape (additions go in transparently thanks to
``extra="allow"`` on the LEAP-mirror models).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .area import Area
from .base import RA3Model
from .button import Button, ButtonGroup, Led
from .controlstation import ControlStation
from .device import Device, RadioRa3Processor
from .programming import Preset, ProgrammingModel
from .project import Project, Server
from .scene import AreaScene, TimeclockEventRule, VirtualButton
from .zone import Zone


class ProcessorInventory(RA3Model):
    """Versioned snapshot of one full processor extraction."""

    schema_version: Literal[1] = 1
    extracted_at: datetime
    source: Literal["live", "fixture", "import"]
    host: str
    """Processor IP at extract time. Debugging aid; do not use as a key."""

    duration_seconds: float
    partial: bool = False
    """True if ``ProjectModifiedTimestamp`` changed mid-walk."""

    processor: RadioRa3Processor
    project: Project
    server: Server | None = None

    areas: list[Area] = Field(default_factory=list)
    devices: list[Device] = Field(default_factory=list)
    """All non-processor devices. Use ``DEVICE_REGISTRY``-typed subclasses
    when the DeviceType is known; falls back to ``Device`` otherwise."""

    zones: list[Zone] = Field(default_factory=list)
    buttons: list[Button] = Field(default_factory=list)
    button_groups: list[ButtonGroup] = Field(default_factory=list)
    leds: list[Led] = Field(default_factory=list)
    control_stations: list[ControlStation] = Field(default_factory=list)
    area_scenes: list[AreaScene] = Field(default_factory=list)
    virtual_buttons: list[VirtualButton] = Field(default_factory=list)
    timeclock_event_rules: list[TimeclockEventRule] = Field(default_factory=list)

    # Resolved cross-references for keypad programming. Keyed by href.
    button_group_expansions: dict[str, list[ButtonGroup]] = Field(default_factory=dict)
    """device href → expanded ButtonGroups (with inline Buttons[])"""

    programming_models: dict[str, ProgrammingModel] = Field(default_factory=dict)
    presets: dict[str, Preset] = Field(default_factory=dict)

    raw_responses: dict[str, Any] | None = None
    """Opt-in debug echo of the unparsed LEAP responses, keyed by URL."""


# ---------------------------------------------------------------------------
# Extraction progress events (streamed via SSE)
# ---------------------------------------------------------------------------


class ExtractionEvent(RA3Model):
    """One progress tick streamed to the UI during an extraction."""

    phase: Literal[
        "connecting",
        "toplevel",
        "devices",
        "zones",
        "buttongroup_expanded",
        "programming_models",
        "presets",
        "indexing",
        "done",
        "error",
    ]
    detail: str
    """Human-readable detail (e.g. ``Pulling /buttongroup`` or ``17 of 21 expansions``)."""

    progress: float | None = None
    """0.0 to 1.0 overall progress estimate. None when phase is indeterminate."""

    error: str | None = None
    """Set only when ``phase == 'error'``."""
