"""Health + version endpoints. No session token required (so the webview
can prove the backend is up before it shows anything else)."""

from __future__ import annotations

from fastapi import APIRouter

from ... import __version__
from ..dto import HealthResponse, VersionResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(version=__version__)


@router.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    return VersionResponse(app_version=__version__, schema_version=1)
