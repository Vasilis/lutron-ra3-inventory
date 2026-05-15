"""Device models with a discriminator registry over ``DeviceType``.

The user's brief enumerates 25+ ``DeviceType`` values. Rather than a literal
union (which would need a code change for every new firmware-added type),
we use a registry: each subclass declares which DeviceType strings it
handles. Unknown types fall back to the ``Device`` base (with
``extra="allow"``) and log a warning — protocol-additive changes don't
crash the extractor.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict

from .base import DeviceFirmwareImage, HrefRef, RA3Resource

_LOG = logging.getLogger(__name__)


class NetworkInterface(BaseModel):
    """Entry in ``RadioRa3Processor.NetworkInterfaces``."""

    model_config = ConfigDict(extra="allow")

    InterfaceType: str | None = None
    MACAddress: str | None = None
    IPv4Address: str | None = None
    IPv4Mask: str | None = None
    IPv4Gateway: str | None = None
    IsPrimary: bool | None = None


class Device(RA3Resource):
    """Base Device — also the fallback for unknown DeviceTypes."""

    Name: str | None = None
    FullyQualifiedName: list[str] | None = None
    DeviceType: str
    ModelNumber: str | None = None
    SerialNumber: int | str | None = None
    """Sometimes int, sometimes string, sometimes null (firmware-dependent)."""

    FirmwareImage: DeviceFirmwareImage | None = None
    AssociatedArea: HrefRef | None = None
    AssociatedControlStation: HrefRef | None = None
    LocalZones: list[HrefRef] = []  # noqa: RUF012 — pydantic handles mutability
    ButtonGroups: list[HrefRef] = []  # noqa: RUF012
    LinkNodes: list[HrefRef] = []  # noqa: RUF012
    AddressedState: str | None = None
    """``Addressed`` / ``Unaddressed`` / ``Unknown`` per the user's brief."""

    DeviceClass: dict | None = None
    DeviceRules: dict | None = None
    Parent: HrefRef | None = None

    @property
    def firmware_display_name(self) -> str | None:
        """Return the firmware display name across known processor shapes."""
        fw = self.FirmwareImage
        if fw is None:
            return None
        if fw.Firmware is not None and fw.Firmware.DisplayName:
            return fw.Firmware.DisplayName

        # RA 3 firmware 26.x moved many device firmware versions under
        # FirmwareImage.Contents[0].OS.Firmware.DisplayName.
        extra = fw.model_extra or {}
        contents = extra.get("Contents") or []
        if not isinstance(contents, list):
            return None
        for item in contents:
            if not isinstance(item, dict):
                continue
            os_block = item.get("OS")
            if not isinstance(os_block, dict):
                continue
            firmware = os_block.get("Firmware")
            if isinstance(firmware, dict) and firmware.get("DisplayName"):
                return str(firmware["DisplayName"])
        return None


DEVICE_REGISTRY: dict[str, type[Device]] = {}


def register_device(*device_types: str):
    """Register a Device subclass against one or more ``DeviceType`` strings."""

    def deco(cls: type[Device]) -> type[Device]:
        for dt in device_types:
            if dt in DEVICE_REGISTRY and DEVICE_REGISTRY[dt] is not cls:
                _LOG.warning(
                    "DeviceType %r already registered to %s, replacing with %s",
                    dt,
                    DEVICE_REGISTRY[dt].__name__,
                    cls.__name__,
                )
            DEVICE_REGISTRY[dt] = cls
        return cls

    return deco


@register_device("RadioRa3Processor")
class RadioRa3Processor(Device):
    """The processor itself. Has network + repeater + database metadata."""

    NetworkInterfaces: list[NetworkInterface] = []  # noqa: RUF012
    OwnedLinks: list[HrefRef] = []  # noqa: RUF012
    Databases: list[Any] = []  # noqa: RUF012
    RepeaterProperties: dict | None = None
    AreaOcupancyMonitorAddress: dict | None = None


@register_device("JanusProcRA3")
class JanusProcRA3(RadioRa3Processor):
    """Older RA 3 processor naming (kept as an alias)."""


# --- Pico remotes -----------------------------------------------------------
# All Pico variants share the same field shape; the discriminator is the
# DeviceType string, and ``button_count`` can be derived from it.

_PICO_BUTTON_COUNTS = {
    "Pico1Button": 1,
    "Pico2Button": 2,
    "Pico2ButtonRaiseLower": 2,
    "Pico3Button": 3,
    "Pico3ButtonRaiseLower": 3,
    "Pico4Button": 4,
    "Pico4ButtonScene": 4,
    "Pico4ButtonZone": 4,
    "Pico4Button2Group": 4,
    "PaddleSwitchPico": 1,
}


@register_device(*_PICO_BUTTON_COUNTS.keys())
class Pico(Device):
    """Pico wireless remote (any variant)."""

    @property
    def button_count(self) -> int:
        return _PICO_BUTTON_COUNTS.get(self.DeviceType, 0)


@register_device("FourGroupRemote", "CasetaFourGroupRemote")
class FourGroupRemote(Device):
    """4-group Caseta scene remote (e.g. ``CS-YJ-4GC``)."""


# --- Keypads ----------------------------------------------------------------


@register_device("SunnataKeypad")
class SunnataKeypad(Device):
    """Sunnata standard keypad (e.g. ``RRST-W4B-XX``, ``RRST-W3RL-XX``)."""


@register_device("SunnataHybridKeypad")
class SunnataHybridKeypad(Device):
    """Sunnata hybrid keypad (e.g. ``RRST-HN3RL-XX``, ``RRST-HN4B-XX``)."""


@register_device(
    "SeeTouchKeypad",
    "SeeTouchHybridKeypad",
    "SeeTouchTabletopKeypad",
    "SeeTouchInternational",
    "GrafikTHybridKeypad",
    "HomeownerKeypad",
    "AlisseKeypad",
    "PalladiomKeypad",
    "PhantomKeypad",
)
class LegacyKeypad(Device):
    """Older/legacy keypad families (HomeWorks QSX + RA 2)."""


@register_device("KeypadLED")
class KeypadLED(Device):
    """Synthetic per-button LED entry. Many of these per keypad."""


# --- Loads (dimmers, switches, fans) ----------------------------------------


@register_device(
    "WallDimmer",
    "PlugInDimmer",
    "InLineDimmer",
    "SunnataDimmer",
    "TempInWallPaddleDimmer",
    "WallDimmerWithPreset",
    "DivaSmartDimmer",
    "PowPak0-10V",
)
class Dimmer(Device):
    """Any dimmed-load device class."""


@register_device(
    "WallSwitch",
    "OutdoorPlugInSwitch",
    "PlugInSwitch",
    "InLineSwitch",
    "PowPakSwitch",
    "SunnataSwitch",
    "TempInWallPaddleSwitch",
    "DivaSmartSwitch",
)
class Switch(Device):
    """Any switched-load device class."""


@register_device(
    "CasetaFanSpeedController",
    "MaestroFanSpeedController",
)
class FanController(Device):
    """Fan-speed controller."""


# --- Shades -----------------------------------------------------------------


@register_device(
    "PalladiomShade",
    "PalladiomWireFreeShade",
    "SivoiaQsTriathlonRollerShade",
    "SivoiaQsTriathlonHoneycombShade",
    "SivoiaQsTriathlonVenetianBlind",
    "TriathlonRollerShade",
    "TriathlonEssentialsRollerShade",
    "TriathlonHoneycombShade",
    "TriathlonTiltOnlyWoodBlind",
    "SerenaCellularShade",
    "SerenaRollerShade",
    "SerenaTiltOnlyWoodBlind",
    "SerenaEssentialsRollerShade",
    "QsWirelessShade",
    "QsWiredShade",
    "QsWirelessHorizontalSheerBlind",
    "QsWirelessWoodBlind",
    "RightDrawDrape",
    "Shade",
    "Tilt",
)
class Shade(Device):
    """Any shade/blind device class."""


# --- Color / tunable-white --------------------------------------------------


@register_device("KetraD3", "SpectrumTune", "WhiteTune", "ColorTune", "DivaColorTune")
class ColorLamp(Device):
    """Ketra-style tunable-white / RGB device."""


# --- Sensors ----------------------------------------------------------------


@register_device(
    "RPSOccupancySensor",
    "RPSCeilingMountedOccupancySensor",
    "RPSWallMountedOccupancySensor",
)
class OccupancySensor(Device):
    """Wireless occupancy sensor."""


def parse_device(raw: dict) -> Device:
    """Construct the right Device subclass from a raw LEAP dict.

    Falls back to the base ``Device`` (with ``extra="allow"``) for unknown
    ``DeviceType`` values; the unknown type is logged once at WARNING.
    """
    device_type = raw.get("DeviceType", "")
    cls = DEVICE_REGISTRY.get(device_type, Device)
    if cls is Device and device_type and device_type not in DEVICE_REGISTRY:
        _LOG.warning("Unknown DeviceType %r — using fallback Device class", device_type)
        DEVICE_REGISTRY.setdefault(device_type, Device)  # log only once
    return cls.model_validate(raw)
