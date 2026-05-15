"""Pairing-cert storage: macOS Keychain primary, encrypted-on-disk fallback.

Provides a single ``materialize_pairing(serial)`` API that returns filesystem
paths for the TLS layer. Keychain- or encrypted-disk-backed credentials are
materialized into a private temporary directory for the duration of one
connection; explicitly plain-disk profiles reuse their existing PEM files.

For M1 we materialize from keychain to disk on every connect; M3+ can
optimize to in-memory SSLContext construction with ``load_cert_chain(data=)``
once we audit that path on PyWebView+briefcase.
"""

from __future__ import annotations

import base64
import logging
import secrets
import shutil
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
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
    temp_dir: Path | None = None

    def cleanup(self) -> None:
        """Delete temporary materialization, if this instance owns one."""
        if self.temp_dir is not None:
            shutil.rmtree(self.temp_dir, ignore_errors=True)


def _derive_fernet_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1, backend=None)
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))


def _encrypted_path(serial: str, name: str) -> Path:
    return certs_dir(serial) / f"{name}.enc"


def _plain_path(serial: str, name: str) -> Path:
    key_path, cert_path, ca_path = cert_paths(serial)
    return {"key": key_path, "cert": cert_path, "ca": ca_path}[name]


def _encrypted_paths(serial: str) -> tuple[Path, Path, Path]:
    return tuple(_encrypted_path(serial, name) for name in ("key", "cert", "ca"))  # type: ignore[return-value]


def has_plain_pairing(serial: str) -> bool:
    """True when a complete plaintext PEM triplet exists on disk."""
    return all(path.exists() for path in cert_paths(serial))


def has_encrypted_pairing(serial: str) -> bool:
    """True when a complete encrypted PEM triplet exists on disk."""
    return (certs_dir(serial) / "salt").exists() and all(
        path.exists() for path in _encrypted_paths(serial)
    )


def has_pairing_on_disk(serial: str) -> bool:
    """True when either supported on-disk credential format is complete."""
    return has_plain_pairing(serial) or has_encrypted_pairing(serial)


def _remove_files(paths: tuple[Path, ...]) -> None:
    for path in paths:
        with suppress(FileNotFoundError):
            path.unlink()


def _write_plain_triplet(
    directory: Path,
    *,
    key_pem: str,
    cert_pem: str,
    ca_pem: str,
) -> CertPaths:
    """Write one PEM triplet into ``directory`` with private permissions."""
    directory.mkdir(parents=True, exist_ok=True)
    with suppress(OSError):
        directory.chmod(0o700)

    paths = CertPaths(
        key=directory / "caseta.key",
        cert=directory / "caseta.crt",
        ca=directory / "caseta-bridge.crt",
    )
    for path, pem in ((paths.key, key_pem), (paths.cert, cert_pem), (paths.ca, ca_pem)):
        path.write_text(pem)
        with suppress(OSError):
            path.chmod(0o600)
    return paths


def _materialize_temp_pairing(key_pem: str, cert_pem: str, ca_pem: str) -> CertPaths:
    temp_dir = Path(tempfile.mkdtemp(prefix="ra3-inventory-certs-"))
    paths = _write_plain_triplet(
        temp_dir,
        key_pem=key_pem,
        cert_pem=cert_pem,
        ca_pem=ca_pem,
    )
    return CertPaths(key=paths.key, cert=paths.cert, ca=paths.ca, temp_dir=temp_dir)


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
        _remove_files((*_encrypted_paths(serial), certs_dir(serial) / "salt"))
        _write_plain_triplet(
            certs_dir(serial),
            key_pem=key_pem,
            cert_pem=cert_pem,
            ca_pem=ca_pem,
        )
        return

    _remove_files(cert_paths(serial))
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
        if not has_plain_pairing(serial):
            return None
        return tuple(p.read_text() for p in paths)  # type: ignore[return-value]

    salt_path = certs_dir(serial) / "salt"
    if not has_encrypted_pairing(serial):
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

    Callers must invoke ``cleanup()`` on the returned ``CertPaths`` after the
    LEAP connection closes. It is a no-op for explicitly plain-disk profiles.
    """
    # 1. Try keychain.
    if keychain.is_available():
        creds = keychain.load_pairing(serial)
        if creds is not None:
            return _materialize_temp_pairing(*creds)

    # 2. Encrypted disk.
    if passphrase is not None:
        creds = load_pairing_from_disk(serial, passphrase=passphrase)
        if creds is not None:
            return _materialize_temp_pairing(*creds)

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
            keychain.store_pairing(
                serial, key_pem=found["key"], cert_pem=found["cert"], ca_pem=found["ca"]
            )
        except Exception:
            _LOG.warning("Failed to mirror imported legacy certs to keychain", exc_info=True)
    return True
