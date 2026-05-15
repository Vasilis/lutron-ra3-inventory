"""Project and server metadata."""

from __future__ import annotations

from pydantic import ConfigDict

from .base import HrefRef, RA3Resource


class Project(RA3Resource):
    """``/project`` — top-level project metadata."""

    Name: str | None = None
    ProductType: str | None = None
    """e.g. 'Lutron RadioRA 3 Project' or 'Lutron Caseta Project'."""

    ProjectModifiedTimestamp: str | dict | None = None
    """The processor returns this in two shapes depending on firmware:

    - A flat ISO8601-ish string, or
    - A ``{"Year": ..., "Month": ..., "Day": ..., "Hour": ..., "Minute": ...,
      "Second": ..., "Utc": "0"}`` dict.

    We accept either; partial-extraction detection compares equality
    against a second reading at the end of the walk, so the structural shape doesn't
    matter as long as both reads agree."""

    MasterDeviceList: dict | None = None
    TimeclockEventRules: HrefRef | None = None


class Server(RA3Resource):
    """``/server/{id}`` — processor server endpoint metadata."""

    model_config = ConfigDict(extra="allow")

    Type: str | None = None
    EnabledState: str | None = None
    LEAPProperties: dict | None = None
    NetworkInterfaces: list[dict] | None = None
