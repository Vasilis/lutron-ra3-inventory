"""Pydantic models for the RA 3 inventory.

Two layers:

* **LEAP-mirror models** (``RA3Resource`` subclasses, ``extra="allow"``):
  Direct mirrors of what the processor sends. PascalCase field names.
  New firmware fields don't break parsing.

* **App-internal DTOs** (``RA3Model`` subclasses, ``extra="forbid"``):
  Our own contracts — API requests/responses, the snapshot envelope, the
  extraction-progress events. Strict.
"""

from .area import Area, area_path
from .base import (
    DeviceFirmwareImage,
    FirmwareImage,
    FirmwareInfo,
    HrefRef,
    InstalledDate,
    RA3Model,
    RA3Resource,
)
from .button import Button, ButtonEngraving, ButtonGroup, Engraving, Led
from .controlstation import ControlStation
from .device import (
    DEVICE_REGISTRY,
    ColorLamp,
    Device,
    Dimmer,
    FanController,
    FourGroupRemote,
    JanusProcRA3,
    KeypadLED,
    LegacyKeypad,
    NetworkInterface,
    OccupancySensor,
    Pico,
    RadioRa3Processor,
    Shade,
    SunnataHybridKeypad,
    SunnataKeypad,
    Switch,
    parse_device,
    register_device,
)
from .programming import Assignment, Preset, ProgrammingModel
from .project import Project, Server
from .scene import AreaScene, TimeclockEventRule, TimeReference, VirtualButton
from .snapshot import ExtractionEvent, ProcessorInventory
from .zone import Zone, ZoneCategory

__all__ = [
    "DEVICE_REGISTRY",
    "Area",
    "AreaScene",
    "Assignment",
    "Button",
    "ButtonEngraving",
    "ButtonGroup",
    "ColorLamp",
    "ControlStation",
    "Device",
    "DeviceFirmwareImage",
    "Dimmer",
    "Engraving",
    "ExtractionEvent",
    "FanController",
    "FirmwareImage",
    "FirmwareInfo",
    "FourGroupRemote",
    "HrefRef",
    "InstalledDate",
    "JanusProcRA3",
    "KeypadLED",
    "Led",
    "LegacyKeypad",
    "NetworkInterface",
    "OccupancySensor",
    "Pico",
    "Preset",
    "ProcessorInventory",
    "ProgrammingModel",
    "Project",
    "RA3Model",
    "RA3Resource",
    "RadioRa3Processor",
    "Server",
    "Shade",
    "SunnataHybridKeypad",
    "SunnataKeypad",
    "Switch",
    "TimeReference",
    "TimeclockEventRule",
    "VirtualButton",
    "Zone",
    "ZoneCategory",
    "area_path",
    "parse_device",
    "register_device",
]
