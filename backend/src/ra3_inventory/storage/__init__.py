"""Storage layer — paths, keychain, encrypted-on-disk certs, snapshots."""

from . import certs, keychain, paths, snapshots
from .certs import CertPaths, import_legacy_certs, materialize_pairing
from .keychain import KeychainUnavailableError
from .paths import APP_NAME, app_data_dir, ensure_profile_tree, profile_dir
from .snapshots import (
    SnapshotSummary,
    list_snapshots,
    read_baseline,
    read_latest,
    read_snapshot,
    set_baseline,
    write_snapshot,
)

__all__ = [
    "APP_NAME",
    "CertPaths",
    "KeychainUnavailableError",
    "SnapshotSummary",
    "app_data_dir",
    "certs",
    "ensure_profile_tree",
    "import_legacy_certs",
    "keychain",
    "list_snapshots",
    "materialize_pairing",
    "paths",
    "profile_dir",
    "read_baseline",
    "read_latest",
    "read_snapshot",
    "set_baseline",
    "snapshots",
    "write_snapshot",
]
