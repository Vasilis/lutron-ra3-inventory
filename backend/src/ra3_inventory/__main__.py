"""Entry point: spawn uvicorn on a worker thread, then launch the webview on the main thread.

The macOS webview MUST run on the main thread; uvicorn doesn't care which
thread it runs on, but it does need its own asyncio event loop, which is why
we spin it up inside ``asyncio.run`` on a worker.

Lifecycle:
1. Load Config (which mints a fresh session_token).
2. Start ``uvicorn.Server.serve()`` in a worker thread, binding to
   ``127.0.0.1:0`` so the OS picks an ephemeral port.
3. Wait for the server to publish its actual port via the socket it
   bound — race-free.
4. Open the system webview at ``http://127.0.0.1:<port>/?token=<token>``.
5. ``webview.start()`` blocks until the window is closed.
6. Cleanly shut the uvicorn server down.

Run with ``RA3INVENTORY_DEV=1`` to enable the webview inspector and FastAPI's
``/docs`` endpoint.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
import time
from concurrent.futures import Future
from typing import Tuple

import uvicorn

from .api import create_app
from .config import Config
from .logging import configure_logging

_LOG = logging.getLogger(__name__)


def _run_uvicorn(server: uvicorn.Server) -> None:
    """Run uvicorn in its own asyncio loop on this thread."""
    asyncio.run(server.serve())


def _wait_for_port(server: uvicorn.Server, port_future: "Future[int]", timeout: float = 10.0) -> None:
    """Watch the server until it has a bound socket, then publish its port."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if server.started and server.servers:
            sock = server.servers[0].sockets[0]
            port = sock.getsockname()[1]
            port_future.set_result(port)
            return
        time.sleep(0.05)
    port_future.set_exception(TimeoutError("uvicorn did not bind a port in time"))


def _start_backend(cfg: Config) -> Tuple[uvicorn.Server, threading.Thread, int]:
    """Start uvicorn on a worker thread. Returns (server, thread, port)."""
    app = create_app(cfg)
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",
        port=0,
        log_level="info",
        access_log=False,
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    server.config.load()  # let uvicorn pick its loop policy synchronously

    port_future: "Future[int]" = Future()

    thread = threading.Thread(
        target=_run_uvicorn, args=(server,), name="ra3-inventory-backend", daemon=True
    )
    thread.start()

    threading.Thread(
        target=_wait_for_port, args=(server, port_future), name="port-discovery", daemon=True
    ).start()

    port = port_future.result(timeout=10)
    return server, thread, port


def main() -> int:
    configure_logging()
    cfg = Config.load()
    cfg.debug = os.environ.get("RA3INVENTORY_DEV") == "1"

    try:
        server, thread, port = _start_backend(cfg)
    except Exception:  # noqa: BLE001
        _LOG.exception("Failed to start backend")
        return 1

    url = f"http://127.0.0.1:{port}/?token={cfg.session_token}"
    _LOG.info("Backend listening on http://127.0.0.1:%d", port)
    _LOG.info("Opening webview at %s", url if cfg.debug else f"http://127.0.0.1:{port}/?token=…")

    try:
        import webview
    except ImportError:
        _LOG.warning(
            "pywebview not installed — running headless. Open %s in a browser to use the app.",
            url,
        )
        try:
            thread.join()
        except KeyboardInterrupt:
            _LOG.info("Interrupted")
        return 0

    window = webview.create_window(
        title="RA3 Inventory",
        url=url,
        width=1280,
        height=820,
        min_size=(960, 640),
    )

    def _on_closed() -> None:
        _LOG.info("Window closed — shutting down backend")
        server.should_exit = True

    window.events.closed += _on_closed
    webview.start(debug=cfg.debug)

    # webview.start() returns when the window is closed. Give uvicorn a beat
    # to drain its tasks.
    deadline = time.time() + 5
    while thread.is_alive() and time.time() < deadline:
        time.sleep(0.1)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
