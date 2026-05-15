"""App-level configuration: paths, session token, port discovery.

A single ``Config`` instance is read from ``app_data_dir() / "config.json"``
at startup (creating defaults if missing) and made available to FastAPI
routes via ``app.state.config``.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field

from .storage.paths import app_data_dir, config_path


@dataclass
class Config:
    """Mutable in-memory app config. Persists to ``config.json``."""

    active_profile_serial: str | None = None
    theme: str = "system"
    """``light`` / ``dark`` / ``system`` — the frontend reads this."""

    session_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    """Per-launch random token. Required on every API call. Not persisted —
    each launch issues a fresh token."""

    debug: bool = False
    """``RA3INVENTORY_DEV=1`` flips this on, exposing the webview inspector
    and FastAPI's /docs."""

    # ----------------------------------------------------------------------

    @classmethod
    def load(cls) -> Config:
        """Load from disk, or seed defaults if no config exists yet."""
        app_data_dir().mkdir(parents=True, exist_ok=True)
        p = config_path()
        if not p.exists():
            cfg = cls()
            cfg.save()
            return cfg
        data = json.loads(p.read_text())
        cfg = cls()
        # Only persist non-secret keys; session_token is always fresh.
        if "active_profile_serial" in data:
            cfg.active_profile_serial = data["active_profile_serial"]
        if "theme" in data:
            cfg.theme = data["theme"]
        return cfg

    def save(self) -> None:
        """Persist non-secret keys."""
        p = config_path()
        p.write_text(
            json.dumps(
                {
                    "active_profile_serial": self.active_profile_serial,
                    "theme": self.theme,
                },
                indent=2,
            )
        )


__all__ = ["Config"]
