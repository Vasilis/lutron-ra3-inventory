"""Profiles CRUD — list, delete (profiles are created by /pair/start)."""

from __future__ import annotations

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status

from ...config import Config
from ...storage import keychain
from ...storage.certs import has_pairing_on_disk
from ...storage.paths import profile_json_path, profiles_dir
from ..deps import get_config, session_dependency
from ..dto import ProfileSummary

router = APIRouter(prefix="/profiles", tags=["profiles"], dependencies=[session_dependency])

_LOG = logging.getLogger(__name__)


@router.get("", response_model=list[ProfileSummary])
async def list_profiles() -> list[ProfileSummary]:
    """List every saved profile."""
    root = profiles_dir()
    if not root.exists():
        return []
    out: list[ProfileSummary] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        serial = entry.name
        meta_path = profile_json_path(serial)
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            _LOG.warning("Skipping malformed profile metadata at %s", meta_path, exc_info=True)
            continue
        last_seen = meta.get("last_seen")
        try:
            parsed_last_seen = datetime.fromisoformat(last_seen) if last_seen else None
        except (TypeError, ValueError):
            parsed_last_seen = None
        out.append(
            ProfileSummary(
                serial=serial,
                name=meta.get("name", serial),
                host=meta.get("host", "?"),
                last_seen=parsed_last_seen,
                firmware=meta.get("firmware"),
                has_certs=has_pairing_on_disk(serial)
                or (keychain.is_available() and keychain.load_pairing(serial) is not None),
            )
        )
    return out


@router.delete("/{serial}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(serial: str, cfg: Config = Depends(get_config)) -> None:
    """Remove a profile and revoke its keychain creds."""
    import shutil

    profile_root = profiles_dir() / serial
    if not profile_root.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no profile {serial}")
    keychain.delete_pairing(serial)
    shutil.rmtree(profile_root)
    if cfg.active_profile_serial == serial:
        cfg.active_profile_serial = None
        cfg.save()
