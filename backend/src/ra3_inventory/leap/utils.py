"""LEAP utility helpers.

Vendored from pylutron-caseta v0.28.0 (Apache-2.0):
https://github.com/gurumitts/pylutron-caseta/blob/v0.28.0/src/pylutron_caseta/utils.py
"""

from __future__ import annotations

import sys

if sys.version_info[:2] < (3, 11):
    from async_timeout import timeout as asyncio_timeout  # type: ignore
else:
    from asyncio import timeout as asyncio_timeout

__all__ = ["asyncio_timeout"]
