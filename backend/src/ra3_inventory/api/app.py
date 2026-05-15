"""FastAPI application factory.

The factory binds:
- ``app.state.config`` — the singleton ``Config``
- ``app.state.event_bus`` — the SSE channel manager

Static frontend assets are mounted from
``backend/src/ra3_inventory/_web/static/`` if that directory has been
populated by the build step.

Same-origin: backend and webview both load from
``http://127.0.0.1:<port>/``, so no CORS configuration is needed.
"""

from __future__ import annotations

import importlib.resources
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..config import Config
from .events import EventBus
from .routes import export, extraction, health, inventory, pairing, profiles, snapshots

_LOG = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Startup/shutdown hook."""
    _LOG.info("ra3-inventory %s starting", __version__)
    yield
    _LOG.info("ra3-inventory %s shutting down", __version__)


def create_app(config: Config | None = None) -> FastAPI:
    cfg = config or Config.load()

    app = FastAPI(
        title="ra3-inventory",
        version=__version__,
        docs_url="/docs" if cfg.debug else None,
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )

    app.state.config = cfg
    app.state.event_bus = EventBus()

    # Routers
    app.include_router(health.router)
    app.include_router(profiles.router)
    app.include_router(pairing.router)
    app.include_router(extraction.router)
    app.include_router(inventory.router)
    app.include_router(snapshots.router)
    app.include_router(export.router)

    # Static frontend assets, if the build step has populated them.
    #
    # StaticFiles(html=True) serves index.html on "/" and falls back to it for
    # any path that doesn't match a real file in the dist (the SPA-routing
    # convention). API routers are registered BEFORE this mount, so they win
    # the matching contest for /health, /profiles, etc.
    try:
        web_root = importlib.resources.files("ra3_inventory") / "_web" / "static"  # type: ignore[arg-type]
        index_html = web_root / "index.html"
        if index_html.is_file():
            app.mount(
                "/",
                StaticFiles(directory=str(web_root), html=True),
                name="frontend",
            )
        else:
            _LOG.info("No frontend dist found — running API-only")
            _attach_placeholder(app)
    except (ModuleNotFoundError, FileNotFoundError):
        _LOG.info("No frontend dist found — running API-only")
        _attach_placeholder(app)

    return app


def _attach_placeholder(app: FastAPI) -> None:
    """Serve a friendly placeholder at ``/`` when the frontend dist isn't built yet.

    Without this, opening the webview URL during backend-only development gets
    a bare ``{"detail": "Not Found"}`` which is alarming. The placeholder
    confirms what's going on and shows the API endpoints that are live.
    """
    from fastapi.responses import HTMLResponse

    @app.get("/", include_in_schema=False)
    async def placeholder() -> HTMLResponse:
        html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>RA3 Inventory — backend running</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, system-ui, sans-serif;
      max-width: 720px; margin: 6rem auto; padding: 0 1.5rem;
      line-height: 1.55; color: #222;
    }
    @media (prefers-color-scheme: dark) { body { color: #eee; background: #111; } }
    h1 { font-weight: 600; margin-bottom: 0.25rem; }
    .sub { opacity: 0.7; margin-top: 0; }
    code, kbd { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.9em; }
    .status { display: inline-block; padding: 0.15em 0.6em; border-radius: 999px;
              background: rgba(34, 197, 94, 0.18); color: #16a34a;
              font-size: 0.85em; font-weight: 500; }
    @media (prefers-color-scheme: dark) { .status { color: #4ade80; } }
    ul { padding-left: 1.25rem; }
    li { margin: 0.3em 0; }
    .muted { opacity: 0.6; font-size: 0.9em; margin-top: 2rem; }
    a { color: inherit; }
  </style>
</head>
<body>
  <p class="status">Backend running · API-only</p>
  <h1>RA3 Inventory</h1>
  <p class="sub">The frontend isn't built yet — that's task #10. The backend is up and ready to serve.</p>

  <h2>Try the API</h2>
  <ul>
    <li><a href="/health"><code>GET /health</code></a> — no auth required</li>
    <li><a href="/version"><code>GET /version</code></a> — no auth required</li>
    <li><code>GET /profiles</code> — needs <code>X-RA3-Token</code> header (or <code>?token=&hellip;</code>)</li>
    <li><code>POST /pair/start</code>, <code>POST /extract</code>, <code>GET /inventory</code>, etc.</li>
  </ul>
  <p class="muted">To build the frontend: when task #10 lands, <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build &amp;&amp; ../scripts/copy-frontend-dist.sh</code>.</p>
</body>
</html>
"""
        return HTMLResponse(html)
