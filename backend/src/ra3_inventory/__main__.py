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

import uvicorn

from .api import create_app
from .config import Config
from .logging import configure_logging

_LOG = logging.getLogger(__name__)


def _run_uvicorn(server: uvicorn.Server) -> None:
    """Run uvicorn in its own asyncio loop on this thread."""
    asyncio.run(server.serve())


def _wait_for_port(server: uvicorn.Server, port_future: Future[int], timeout: float = 10.0) -> None:
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


def _start_backend(cfg: Config) -> tuple[uvicorn.Server, threading.Thread, int]:
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

    port_future: Future[int] = Future()

    thread = threading.Thread(
        target=_run_uvicorn, args=(server,), name="ra3-inventory-backend", daemon=True
    )
    thread.start()

    threading.Thread(
        target=_wait_for_port, args=(server, port_future), name="port-discovery", daemon=True
    ).start()

    port = port_future.result(timeout=10)
    return server, thread, port


class JsApi:
    """Bridge functions exposed to JavaScript as ``window.pywebview.api.*``.

    These exist because two web-platform features that the React frontend
    needs are blocked in the embedded WKWebView:

    - **Downloads.** ``<a download>`` is treated as a navigation, with no
      back button, so it can't be used to save an export to disk.
    - **Clipboard.** ``navigator.clipboard.writeText`` requires permissions
      that the default WKWebView config in PyWebView doesn't grant.

    Routing through Python sidesteps both: ``save_file`` opens a real
    Cocoa save panel and writes bytes; ``copy_text`` puts a string on
    the NSPasteboard.
    """

    def __init__(self) -> None:
        self._window = None

    def bind_window(self, window) -> None:
        """Called once after ``create_window``."""
        self._window = window

    def save_file(self, filename: str, content_b64: str) -> dict:
        """Open a native Save panel, write ``content_b64`` (base64-decoded)
        to the chosen path. Returns ``{ok, path, error}``."""
        import base64

        if self._window is None:
            return {"ok": False, "error": "no active window"}
        import webview

        try:
            result = self._window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=filename,
            )
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)}
        if not result:
            return {"ok": False, "error": "cancelled"}

        path = result if isinstance(result, str) else result[0]
        try:
            data = base64.b64decode(content_b64)
            from pathlib import Path

            Path(path).write_bytes(data)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)}
        return {"ok": True, "path": str(path)}

    def copy_text(self, text: str) -> dict:
        """Put ``text`` on the system clipboard. macOS NSPasteboard."""
        try:
            # Lazy import — only needed when the frontend asks for a copy.
            from AppKit import NSPasteboard  # type: ignore[import-not-found]

            pb = NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(text, "public.utf8-plain-text")
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": repr(exc)}


def main() -> int:
    configure_logging()
    cfg = Config.load()
    cfg.debug = os.environ.get("RA3INVENTORY_DEV") == "1"

    try:
        server, thread, port = _start_backend(cfg)
    except Exception:
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

    # JS bridge exposed as ``window.pywebview.api.*`` — gives the frontend
    # a way to trigger a native save dialog (downloads via ``<a download>``
    # don't work reliably in WKWebView) and to write text to the system
    # clipboard (the JS clipboard API requires permissions WKWebView
    # doesn't grant by default).
    js_api = JsApi()
    window = webview.create_window(
        title="RA3 Inventory",
        url=url,
        width=1280,
        height=820,
        min_size=(960, 640),
        js_api=js_api,
    )
    js_api.bind_window(window)

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
