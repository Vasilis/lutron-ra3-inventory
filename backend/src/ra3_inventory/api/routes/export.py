"""Export routes — JSON / Markdown / CSV-zip / XLSX downloads."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from ...export import to_csv_zip, to_json_bytes, to_markdown, to_xlsx
from ...sanitize import sanitize_inventory
from ..deps import LatestInventoryDep, session_dependency

router = APIRouter(prefix="/export", tags=["export"], dependencies=[session_dependency])


def _content_disposition(filename: str) -> dict[str, str]:
    return {"Content-Disposition": f'attachment; filename="{filename}"'}


def _selected_inventory(inv: LatestInventoryDep, sanitized: bool):
    return sanitize_inventory(inv) if sanitized else inv


@router.get("/json")
async def export_json(inv: LatestInventoryDep, sanitized: bool = False) -> Response:
    body = to_json_bytes(_selected_inventory(inv, sanitized))
    return Response(
        content=body,
        media_type="application/json",
        headers=_content_disposition("inventory-sanitized.json" if sanitized else "inventory.json"),
    )


@router.get("/markdown")
async def export_markdown(
    inv: LatestInventoryDep,
    sanitized: bool = False,
    sections: str | None = None,
) -> Response:
    """Render Markdown.

    ``sections``: optional comma-separated list of section keys (see
    ``backend/src/ra3_inventory/export/markdown_export.py:SECTION_KEYS``).
    When supplied, only those sections are emitted; when absent, all
    sections are included (legacy behavior).
    """
    section_set: set[str] | None = None
    if sections is not None:
        section_set = {s.strip() for s in sections.split(",") if s.strip()}

    body = to_markdown(_selected_inventory(inv, sanitized), sections=section_set).encode("utf-8")
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers=_content_disposition("inventory-sanitized.md" if sanitized else "inventory.md"),
    )


@router.get("/csv")
async def export_csv(inv: LatestInventoryDep, sanitized: bool = False) -> Response:
    body = to_csv_zip(_selected_inventory(inv, sanitized))
    return Response(
        content=body,
        media_type="application/zip",
        headers=_content_disposition("inventory-sanitized.zip" if sanitized else "inventory.zip"),
    )


@router.get("/xlsx")
async def export_xlsx(inv: LatestInventoryDep, sanitized: bool = False) -> Response:
    body = to_xlsx(_selected_inventory(inv, sanitized))
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_content_disposition("inventory-sanitized.xlsx" if sanitized else "inventory.xlsx"),
    )
