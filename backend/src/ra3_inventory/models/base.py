"""Shared base types for LEAP-mirrored Pydantic models.

These models keep Lutron's PascalCase field names verbatim. The export layer
is the only place that converts to snake_case (and only with an explicit
flag). Internal code and the API always sees PascalCase, which makes
debugging against pcaps trivial.

``RA3Resource`` carries ``extra="allow"`` so new firmware fields don't break
deserialization. App-internal DTOs (API request/response, snapshot envelope)
inherit from ``RA3Model`` instead, which is ``extra="forbid"``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RA3Model(BaseModel):
    """App-internal DTO base. Strict — unknown fields are an error."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class RA3Resource(BaseModel):
    """Base for anything parsed from a raw LEAP response.

    Unknown fields are preserved (``extra="allow"``) so additive firmware
    changes don't break the parser. Every LEAP resource has an ``href``.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    href: str


class HrefRef(BaseModel):
    """A reference to another LEAP resource by href."""

    model_config = ConfigDict(extra="allow")

    href: str


class FirmwareInfo(BaseModel):
    """The firmware version block inside ``FirmwareImage.Firmware``."""

    model_config = ConfigDict(extra="allow")

    DisplayName: str | None = None


class InstalledDate(BaseModel):
    """Timestamp of when firmware was installed (``FirmwareImage.Installed``)."""

    model_config = ConfigDict(extra="allow")

    Year: int | None = None
    Month: int | None = None
    Day: int | None = None
    Hour: int | None = None
    Minute: int | None = None
    Second: int | None = None
    Utc: str | None = None


class FirmwareImage(BaseModel):
    """``Device.FirmwareImage`` — display name + installation timestamp."""

    model_config = ConfigDict(extra="allow")

    Firmware: FirmwareInfo | None = None
    Installed: InstalledDate | None = None
