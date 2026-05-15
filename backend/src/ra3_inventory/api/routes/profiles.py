"""Profiles CRUD — list, delete (profiles are created by /pair/start)."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from ...storage import keychain
from ...storage.paths import cert_paths, profile_json_path, profiles_dir
from ..deps import SessionDep
from ..dto import ProfileSummary

router = APIRouter(prefix="/profiles", tags=["profiles"], dependencies=[SessionDep])


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
        except Exception:  # noqa: BLE001
            continue
        last_seen = meta.get("last_seen")
        out.append(ProfileSummary(
            serial=serial,
            name=meta.get("name", serial),
            host=meta.get("host", "?"),
            last_seen=datetime.fromisoformat(last_seen) if last_seen else None,
            firmware=meta.get("firmware"),
            has_certs=all(p.exists() for p in cert_paths(serial)) or keychain.load_pairing(serial) is not None,
        ))
    return out


@router.delete("/{serial}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(serial: str) -> None:
    """Remove a profile and revoke its keychain creds."""
    import shutil

    profile_root = profiles_dir() / serial
    if not profile_root.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no profile {serial}")
    keychain.delete_pairing(serial)
    shutil.rmtree(profile_root)
