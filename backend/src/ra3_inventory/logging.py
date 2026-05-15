"""App logging setup.

Logs go to a rotating file under
``~/Library/Application Support/RA3Inventory/logs/ra3-inventory.log``
and to stderr (level INFO unless ``RA3INVENTORY_DEV=1`` flips DEBUG on).
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path

from .storage.paths import logs_dir

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(level: int | None = None) -> None:
    if level is None:
        level = logging.DEBUG if os.environ.get("RA3INVENTORY_DEV") == "1" else logging.INFO

    logs = logs_dir()
    logs.mkdir(parents=True, exist_ok=True)
    log_file: Path = logs / "ra3-inventory.log"

    root = logging.getLogger()
    root.setLevel(level)

    # Wipe any handlers seeded by libs at import time.
    for h in list(root.handlers):
        root.removeHandler(h)

    stderr = logging.StreamHandler(sys.stderr)
    stderr.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(stderr)

    fileh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=3
    )
    fileh.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(fileh)

    # Quiet a few chatty third-party loggers
    for name in ("urllib3", "asyncio", "watchfiles"):
        logging.getLogger(name).setLevel(logging.WARNING)
