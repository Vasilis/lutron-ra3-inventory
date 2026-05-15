"""Filesystem paths for app data on macOS.

Layout under ``~/Library/Application Support/RA3Inventory/``:

::

    config.json                       app prefs (active profile, theme)
    logs/                             rotating app logs
    profiles/
      <serial>/                       profile dir, keyed by processor SerialNumber
        profile.json                  display name, host, last-seen, firmware
        certs/                        PEM fallback (mode 0600)
          caseta.key                  client private key
          caseta.crt                  client cert
          caseta-bridge.crt           processor CA cert
        snapshots/
          2026-05-15T14-30-00Z.json   one per extraction
          latest.json                 hardlink to most recent
          baseline.json               user-pinned baseline (for M4 diff)

Legacy cert names (``caseta.key/crt``, ``caseta-bridge.crt``) are preserved
so users with existing pairings from the standalone scripts can drop them
straight in without re-pairing.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "RA3Inventory"


def app_data_dir() -> Path:
    """The root data directory for this app on the current OS."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    if sys.platform == "win32":
        # AppData\Roaming\<AppName>
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME
    # XDG on Linux/BSD
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def config_path() -> Path:
    return app_data_dir() / "config.json"


def logs_dir() -> Path:
    return app_data_dir() / "logs"


def profiles_dir() -> Path:
    return app_data_dir() / "profiles"


def profile_dir(serial: str) -> Path:
    return profiles_dir() / serial


def profile_json_path(serial: str) -> Path:
    return profile_dir(serial) / "profile.json"


def certs_dir(serial: str) -> Path:
    return profile_dir(serial) / "certs"


def cert_paths(serial: str) -> tuple[Path, Path, Path]:
    """Return ``(key, cert, ca)`` paths for a profile."""
    d = certs_dir(serial)
    return d / "caseta.key", d / "caseta.crt", d / "caseta-bridge.crt"


def snapshots_dir(serial: str) -> Path:
    return profile_dir(serial) / "snapshots"


def latest_snapshot_path(serial: str) -> Path:
    return snapshots_dir(serial) / "latest.json"


def baseline_snapshot_path(serial: str) -> Path:
    return snapshots_dir(serial) / "baseline.json"


def ensure_profile_tree(serial: str) -> None:
    """Create the directory tree for a profile if missing. Sets 0700 on the certs dir."""
    profile_dir(serial).mkdir(parents=True, exist_ok=True)
    cdir = certs_dir(serial)
    cdir.mkdir(parents=True, exist_ok=True)
    try:
        cdir.chmod(0o700)
    except OSError:
        pass
    snapshots_dir(serial).mkdir(parents=True, exist_ok=True)
    logs_dir().mkdir(parents=True, exist_ok=True)
