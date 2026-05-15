"""macOS Keychain wrapper for storing pairing credentials.

Uses the cross-platform ``keyring`` library, which on macOS talks to the
Security framework through the system Keychain. On Linux this would route
to Secret Service / GNOME Keyring, on Windows to the Credential Manager —
but for v1 we're macOS-only.

Three Keychain items per processor profile:
    service: ``com.ra3inventory.<serial>``
    accounts: ``key``, ``cert``, ``ca``

When the user opts out of Keychain or it's unavailable, ``storage.certs``
provides an encrypted on-disk fallback.
"""

from __future__ import annotations

import logging
from typing import Literal

try:
    import keyring
    import keyring.errors

    _HAS_KEYRING = True
except ImportError:  # pragma: no cover — runtime-required
    _HAS_KEYRING = False

_LOG = logging.getLogger(__name__)

SERVICE_PREFIX = "com.ra3inventory"

CredKind = Literal["key", "cert", "ca"]


def _service(serial: str) -> str:
    return f"{SERVICE_PREFIX}.{serial}"


class KeychainUnavailableError(RuntimeError):
    """Raised when the keyring backend isn't usable on this system."""


def is_available() -> bool:
    """True if the keyring backend can be reached."""
    if not _HAS_KEYRING:
        return False
    try:
        # Probing for a non-existent key shouldn't raise; if it does the
        # backend is unhealthy.
        keyring.get_password(SERVICE_PREFIX + ".probe", "probe")
        return True
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("Keyring backend unavailable: %r", exc)
        return False


def store_pairing(serial: str, *, key_pem: str, cert_pem: str, ca_pem: str) -> None:
    """Write the three pairing items into the platform keychain."""
    if not _HAS_KEYRING:
        raise KeychainUnavailableError("python-keyring is not installed")
    service = _service(serial)
    keyring.set_password(service, "key", key_pem)
    keyring.set_password(service, "cert", cert_pem)
    keyring.set_password(service, "ca", ca_pem)
    _LOG.info("Stored pairing credentials in keychain for %s", serial)


def load_pairing(serial: str) -> tuple[str, str, str] | None:
    """Return ``(key_pem, cert_pem, ca_pem)`` if all three are present, else None."""
    if not _HAS_KEYRING:
        return None
    service = _service(serial)
    key = keyring.get_password(service, "key")
    cert = keyring.get_password(service, "cert")
    ca = keyring.get_password(service, "ca")
    if key and cert and ca:
        return key, cert, ca
    return None


def delete_pairing(serial: str) -> None:
    """Remove all three keychain items for a profile (idempotent)."""
    if not _HAS_KEYRING:
        return
    service = _service(serial)
    for account in ("key", "cert", "ca"):
        try:
            keyring.delete_password(service, account)
        except keyring.errors.PasswordDeleteError:
            pass
