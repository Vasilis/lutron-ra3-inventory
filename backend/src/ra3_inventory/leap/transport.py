"""TLS transport for an authenticated LEAP connection.

Extracted from pylutron-caseta v0.28.0 ``smartbridge.py`` (Apache-2.0):
https://github.com/gurumitts/pylutron-caseta/blob/v0.28.0/src/pylutron_caseta/smartbridge.py

Modified: lifted ``_create_tls_context`` and the ``create_tls`` connect path
out of the ``Smartbridge`` class. This module exposes a single ``connect_leap``
coroutine that opens a TLS stream and returns a ready-to-use ``LeapProtocol``,
without any of the parsed Smartbridge state machine.
"""

from __future__ import annotations

import asyncio
import socket
import ssl
from pathlib import Path
from typing import Union

from ._const import LEAP_PORT
from .protocol import LeapProtocol, open_connection

PathLike = Union[str, Path]


def _create_tls_context(
    keyfile: PathLike,
    certfile: PathLike,
    ca_certs: PathLike,
) -> ssl.SSLContext:
    """Build a client TLS context pinning the processor's CA.

    Called inside a thread executor because ``load_cert_chain`` and
    ``load_verify_locations`` do blocking disk I/O.
    """
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
    ssl_context.load_verify_locations(str(ca_certs))
    ssl_context.load_cert_chain(str(certfile), str(keyfile))
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    return ssl_context


async def connect_leap(
    host: str,
    keyfile: PathLike,
    certfile: PathLike,
    ca_certs: PathLike,
    port: int = LEAP_PORT,
) -> LeapProtocol:
    """Open an authenticated TLS connection to a Lutron processor and return a LeapProtocol.

    The TLS handshake disables hostname verification (``server_hostname=""``) because
    the processor's certificate uses its serial-derived name, not a DNS hostname.
    Identity is established via the pinned CA certificate from pairing.
    """
    loop = asyncio.get_running_loop()
    ssl_context = await loop.run_in_executor(
        None, _create_tls_context, keyfile, certfile, ca_certs
    )
    return await open_connection(
        host,
        port,
        server_hostname="",
        ssl=ssl_context,
        family=socket.AF_INET,
    )
