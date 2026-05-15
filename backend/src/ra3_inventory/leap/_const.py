"""LEAP protocol constants.

Vendored from pylutron-caseta v0.28.0 (Apache-2.0):
constants previously inlined in ``pylutron_caseta/smartbridge.py`` and
``pylutron_caseta/pairing.py``.
"""

from __future__ import annotations

LEAP_PORT: int = 8081
"""TCP port for the production LEAP TLS connection."""

PAIR_PORT: int = 8083
"""TCP port for the initial pairing handshake."""

SOCKET_TIMEOUT: float = 10.0
"""Default timeout for short socket operations during pairing (seconds)."""

BUTTON_PRESS_TIMEOUT: float = 180.0
"""How long to wait for the user to press the pairing button (seconds)."""

PING_INTERVAL: float = 60.0
"""Keepalive ping cadence on a live LEAP connection (seconds)."""

REQUEST_TIMEOUT: float = 5.0
"""Default timeout for a single LEAP request (seconds)."""

RECONNECT_DELAY: float = 2.0
"""Backoff between reconnect attempts after an unexpected disconnect (seconds)."""
