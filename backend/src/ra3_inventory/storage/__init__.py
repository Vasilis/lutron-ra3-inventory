"""Storage layer — paths, keychain, encrypted-on-disk certs, snapshots."""

from . import certs, keychain, paths, snapshots
from .certs import (
    CertPaths,
    has_encrypted_pairing,
    has_pairing_on_disk,
    has_plain_pairing,
    import_legacy_certs,
    materialize_pairing,
)
from .keychain import KeychainUnavailableError
from .paths import APP_NAME, app_data_dir, ensure_profile_tree, profile_dir
from .snapshots import (
    SnapshotSummary,
    delete_snapshot,
    list_snapshots,
    prune_snapshots,
    read_baseline,
    read_latest,
    read_snapshot,
    set_baseline,
    snapshot_path,
    write_snapshot,
)

__all__ = [
    "APP_NAME",
    "CertPaths",
    "KeychainUnavailableError",
    "SnapshotSummary",
    "app_data_dir",
    "certs",
    "delete_snapshot",
    "ensure_profile_tree",
    "has_encrypted_pairing",
    "has_pairing_on_disk",
    "has_plain_pairing",
    "import_legacy_certs",
    "keychain",
    "list_snapshots",
    "materialize_pairing",
    "paths",
    "profile_dir",
    "prune_snapshots",
    "read_baseline",
    "read_latest",
    "read_snapshot",
    "set_baseline",
    "snapshot_path",
    "snapshots",
    "write_snapshot",
]
