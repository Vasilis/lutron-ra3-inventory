"""FastAPI dependencies — token check, active profile resolver, snapshot loader."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from ..config import Config
from ..models import ProcessorInventory
from ..storage import read_latest
from ..storage.paths import validate_profile_serial


def get_config(request: Request) -> Config:
    return request.app.state.config


def require_session(
    cfg: Annotated[Config, Depends(get_config)],
    x_ra3_token: Annotated[str | None, Header(alias="X-RA3-Token")] = None,
    token: str | None = None,  # also allow ?token= for the initial webview URL
) -> None:
    """Reject requests that don't carry the per-launch session token."""
    supplied = x_ra3_token or token
    if supplied != cfg.session_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid session token")


def active_profile_serial(
    cfg: Annotated[Config, Depends(get_config)],
) -> str:
    if cfg.active_profile_serial is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no active profile — pair first")
    try:
        return validate_profile_serial(cfg.active_profile_serial)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "active profile is invalid") from exc


def latest_inventory(
    serial: Annotated[str, Depends(active_profile_serial)],
) -> ProcessorInventory:
    inv = read_latest(serial)
    if inv is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"no snapshot for profile {serial} — run /extract first",
        )
    return inv


SessionDep = Annotated[None, Depends(require_session)]
ActiveSerialDep = Annotated[str, Depends(active_profile_serial)]
LatestInventoryDep = Annotated[ProcessorInventory, Depends(latest_inventory)]

# Router-level dependency (use in ``APIRouter(dependencies=[...])``). The
# ``Annotated`` aliases above are only valid as function-parameter types.
session_dependency = Depends(require_session)
