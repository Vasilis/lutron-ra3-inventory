"""Request/response DTOs for the API layer.

All ``RA3Model`` subclasses (``extra="forbid"``) — strict wire contracts.
Distinct from the LEAP-mirror models which are ``extra="allow"`` and
PascalCase to match the protocol.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from ..models import RA3Model


# ---- Profiles -------------------------------------------------------------


class ProfileSummary(RA3Model):
    """Summary entry for the profiles list."""

    serial: str
    name: str
    host: str
    last_seen: datetime | None = None
    firmware: str | None = None
    has_certs: bool


class ProfileCreate(RA3Model):
    name: str
    host: str


class ProfileCreated(RA3Model):
    serial: str
    name: str
    host: str


# ---- Pairing --------------------------------------------------------------


class PairStartRequest(RA3Model):
    host: str
    name: str = "Default"


class PairStartResponse(RA3Model):
    pair_id: str


# ---- Extraction -----------------------------------------------------------


class ExtractStartRequest(RA3Model):
    profile_serial: str
    capture_raw: bool = False


class ExtractStartResponse(RA3Model):
    extract_id: str


# ---- Snapshots ------------------------------------------------------------


class SnapshotEntry(RA3Model):
    filename: str
    extracted_at: datetime
    host: str
    is_latest: bool
    is_baseline: bool
    size_bytes: int


class SetBaselineRequest(RA3Model):
    filename: str


# ---- System ---------------------------------------------------------------


class HealthResponse(RA3Model):
    status: Literal["ok"] = "ok"
    version: str


class VersionResponse(RA3Model):
    app_version: str
    schema_version: int


# ---- Inventory list filters ----------------------------------------------


class DeviceFilter(RA3Model):
    device_type: str | None = Field(default=None, alias="type")
