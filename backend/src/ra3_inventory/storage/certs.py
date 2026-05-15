"""Pairing-cert storage: macOS Keychain primary, encrypted-on-disk fallback.

Provides a single ``CertStore.load(serial)`` API that materializes the three
PEMs onto disk in a profile's ``certs/`` directory and returns their paths
(so the LEAP TLS layer can ``load_cert_chain`` them via ``str``). On a clean
shutdown the temp materialization is cleared; if the app crashes the on-disk
PEMs remain, encrypted-or-not depending on which mode the user chose.

For M1 we materialize from keychain to disk on every connect; M3+ can
optimize to in-memory SSLContext construction with ``load_cert_chain(data=)``
once we audit that path on PyWebView+briefcase.
"""

from __future__ import annotations

import base64
import logging
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from . import keychain
from .paths import cert_paths, certs_dir, ensure_profile_tree

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class CertPaths:
    """Materialized cert file paths for a profile."""

    key: Path
    cert: Path
    ca: Path


def _derive_fernet_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1, backend=None)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _encrypted_path(serial: str, name: str) -> Path:
    return certs_dir(serial) / f"{name}.enc"


def _plain_path(serial: str, name: str) -> Path:
    key_path, cert_path, ca_path = cert_paths(serial)
    return {"key": key_path, "cert": cert_path, "ca": ca_path}[name]


def store_pairing_to_disk(
    serial: str,
    *,
    key_pem: str,
    cert_pem: str,
    ca_pem: str,
    passphrase: str | None = None,
) -> None:
    """Persist pairing PEMs to ``profiles/<serial>/certs/``.

    If ``passphrase`` is set, the three files are Fernet-encrypted with a
    scrypt-derived key. Otherwise they're written plain with mode 0600.
    """
    ensure_profile_tree(serial)

    if passphrase is None:
        for name, pem in (("key", key_pem), ("cert", cert_pem), ("ca", ca_pem)):
            p = _plain_path(serial, name)
            p.write_text(pem)
            try:
                p.chmod(0o600)
            except OSError:
                pass
        return

    salt = secrets.token_bytes(16)
    fkey = _derive_fernet_key(passphrase, salt)
    fernet = Fernet(fkey)
    salt_path = certs_dir(serial) / "salt"
    salt_path.write_bytes(salt)
    salt_path.chmod(0o600)
    for name, pem in (("key", key_pem), ("cert", cert_pem), ("ca", ca_pem)):
        token = fernet.encrypt(pem.encode("utf-8"))
        p = _encrypted_path(serial, name)
        p.write_bytes(token)
        p.chmod(0o600)


def load_pairing_from_disk(
    serial: str, passphrase: str | None = None
) -> tuple[str, str, str] | None:
    """Return ``(key_pem, cert_pem, ca_pem)`` from on-disk storage, or None."""
    if passphrase is None:
        paths = cert_paths(serial)
        if not all(p.exists() for p in paths):
            return None
        return tuple(p.read_text() for p in paths)  # type: ignore[return-value]

    salt_path = certs_dir(serial) / "salt"
    if not salt_path.exists():
        return None
    salt = salt_path.read_bytes()
    fkey = _derive_fernet_key(passphrase, salt)
    fernet = Fernet(fkey)
    out: list[str] = []
    for name in ("key", "cert", "ca"):
        p = _encrypted_path(serial, name)
        if not p.exists():
            return None
        try:
            out.append(fernet.decrypt(p.read_bytes()).decode("utf-8"))
        except InvalidToken:
            _LOG.warning("Bad passphrase for %s/%s", serial, name)
            return None
    return out[0], out[1], out[2]


def materialize_pairing(
    serial: str,
    *,
    passphrase: str | None = None,
) -> CertPaths | None:
    """Resolve pairing creds (keychain → encrypted disk → plain disk) and
    return three filesystem paths the SSL layer can use.

    For M1 this writes the three PEMs to the profile's ``certs/`` directory
    if they came from the keychain — the LEAP TLS layer needs file paths
    (``ssl_context.load_cert_chain(certfile, keyfile)``). When we move to
    in-memory cert loading this materialization step can disappear.
    """
    # 1. Try keychain.
    if keychain.is_available():
        creds = keychain.load_pairing(serial)
        if creds is not None:
            store_pairing_to_disk(serial, key_pem=creds[0], cert_pem=creds[1], ca_pem=creds[2])
            key_p, cert_p, ca_p = cert_paths(serial)
            return CertPaths(key=key_p, cert=cert_p, ca=ca_p)

    # 2. Encrypted disk.
    if passphrase is not None:
        creds = load_pairing_from_disk(serial, passphrase=passphrase)
        if creds is not None:
            # Decrypted creds — materialize to plain temp files only during
            # the active connection. Caller is responsible for cleanup.
            store_pairing_to_disk(serial, key_pem=creds[0], cert_pem=creds[1], ca_pem=creds[2])
            key_p, cert_p, ca_p = cert_paths(serial)
            return CertPaths(key=key_p, cert=cert_p, ca=ca_p)

    # 3. Plain on disk.
    creds = load_pairing_from_disk(serial)
    if creds is not None:
        key_p, cert_p, ca_p = cert_paths(serial)
        return CertPaths(key=key_p, cert=cert_p, ca=ca_p)

    return None


def import_legacy_certs(legacy_dir: Path, serial: str) -> bool:
    """Copy certs from a ``./lutron_certs/`` style legacy directory into a profile.

    Returns True if all three expected PEMs were imported.
    """
    expected = {
        "caseta.key": "key",
        "caseta.crt": "cert",
        "caseta-bridge.crt": "ca",
    }
    found: dict[str, str] = {}
    for fname, kind in expected.items():
        p = legacy_dir / fname
        if not p.exists():
            return False
        found[kind] = p.read_text()
    store_pairing_to_disk(serial, key_pem=found["key"], cert_pem=found["cert"], ca_pem=found["ca"])
    if keychain.is_available():
        try:
            keychain.store_pairing(serial, key_pem=found["key"], cert_pem=found["cert"], ca_pem=found["ca"])
        except Exception:  # noqa: BLE001
            _LOG.warning("Failed to mirror imported legacy certs to keychain", exc_info=True)
    return True
