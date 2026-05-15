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
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .. import __version__
from ..config import Config
from .events import EventBus
from .routes import export, extraction, health, inventory, pairing, profiles, snapshots

_LOG = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
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

    # Static frontend assets, if the build step has populated them
    try:
        web_root = importlib.resources.files("ra3_inventory") / "_web" / "static"  # type: ignore[arg-type]
        index_html = web_root / "index.html"
        if index_html.is_file():
            app.mount("/static", StaticFiles(directory=str(web_root)), name="static")

            @app.get("/")
            async def serve_index() -> FileResponse:
                return FileResponse(str(index_html))

            # SPA fallback: any non-API GET that doesn't match a route serves index.html.
            @app.get("/{full_path:path}")
            async def spa_fallback(full_path: str) -> FileResponse | JSONResponse:
                # Don't shadow the OpenAPI docs or API routes.
                if full_path.startswith(("api/", "docs", "openapi.json", "health",
                                         "version", "profiles", "pair", "extract",
                                         "inventory", "snapshots", "export", "static")):
                    return JSONResponse({"detail": "Not Found"}, status_code=404)
                return FileResponse(str(index_html))
        else:
            _LOG.info("No frontend dist found — running API-only")
    except (ModuleNotFoundError, FileNotFoundError):
        _LOG.info("No frontend dist found — running API-only")

    return app
