"""High-level facade — connect → extract → disconnect, in one call.

This is the entry point most code should use. It hides the TLS-connect dance,
the LeapProtocol task lifecycle, and the cleanup-on-error pattern. Callers
provide cert paths, a host, and (optionally) a progress callback for SSE
streaming, and receive a fully typed ``ProcessorInventory``.

The processor only allows one LEAP connection at a time. Coordinate with any
Home Assistant / HomeBridge clients before calling.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..models import ProcessorInventory
from ._const import LEAP_PORT
from .extract import InventoryExtractor, ProgressFn
from .protocol import LeapProtocol
from .transport import connect_leap

_LOG = logging.getLogger(__name__)


class AlreadyConnectedError(RuntimeError):
    """Raised when another LEAP client is currently holding the processor's connection.

    The processor only accepts one LEAP connection at a time. UI surfaces should
    catch this and prompt the user to close Home Assistant / HomeBridge / etc.
    """


async def extract_inventory(
    *,
    host: str,
    keyfile: str | Path,
    certfile: str | Path,
    ca_certs: str | Path,
    port: int = LEAP_PORT,
    on_progress: ProgressFn = None,
    capture_raw: bool = False,
) -> ProcessorInventory:
    """Connect, pull the full inventory, disconnect, return typed result.

    Args:
        host: Processor IP or hostname.
        keyfile: Path to the client private key PEM.
        certfile: Path to the client cert PEM.
        ca_certs: Path to the processor's CA cert PEM.
        port: LEAP TLS port (default 8081).
        on_progress: Optional callback receiving ``ExtractionEvent``s in real
            time. Can be sync or async.
        capture_raw: If True, include the unparsed LEAP responses keyed by URL
            in ``ProcessorInventory.raw_responses``. Useful for debugging.

    Raises:
        AlreadyConnectedError: Another LEAP client owns the processor.
        ConnectionError: Network or TLS handshake failure.
    """
    _LOG.info("Opening LEAP connection to %s:%d", host, port)
    try:
        proto: LeapProtocol = await connect_leap(
            host, keyfile=keyfile, certfile=certfile, ca_certs=ca_certs, port=port
        )
    except ConnectionRefusedError as exc:
        # The processor will refuse a second TLS handshake while another LEAP
        # client holds the connection. There's no clean way to distinguish this
        # from "processor offline" — heuristically, refusal-after-route-is-up
        # almost always means contention.
        raise AlreadyConnectedError(
            f"{host}:{port} refused the connection — another LEAP client "
            "(Home Assistant, HomeBridge, the Lutron app) may be connected. "
            "Close it and try again."
        ) from exc

    try:
        extractor = InventoryExtractor(
            proto=proto,
            host=host,
            on_progress=on_progress,
            capture_raw=capture_raw,
        )
        return await extractor.run()
    finally:
        try:
            proto.close()
            await proto.wait_closed()
        except Exception:
            _LOG.debug("Error during LeapProtocol shutdown", exc_info=True)
