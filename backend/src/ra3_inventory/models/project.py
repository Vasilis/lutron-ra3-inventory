"""Project and server metadata."""

from __future__ import annotations

from pydantic import ConfigDict

from .base import HrefRef, RA3Resource


class Project(RA3Resource):
    """``/project`` — top-level project metadata."""

    Name: str | None = None
    ProductType: str | None = None
    """e.g. 'Lutron RadioRA 3 Project' or 'Lutron Caseta Project'."""

    ProjectModifiedTimestamp: str | None = None
    """ISO8601-ish string emitted by the processor. Used to detect Designer
    pushes mid-extraction."""

    MasterDeviceList: dict | None = None
    TimeclockEventRules: HrefRef | None = None


class Server(RA3Resource):
    """``/server/{id}`` — processor server endpoint metadata."""

    model_config = ConfigDict(extra="allow")

    Type: str | None = None
    EnabledState: str | None = None
    LEAPProperties: dict | None = None
    NetworkInterfaces: list[dict] | None = None
