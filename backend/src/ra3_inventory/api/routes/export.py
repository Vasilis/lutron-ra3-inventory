"""Export routes — JSON / Markdown / CSV-zip / XLSX downloads."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from ...export import to_csv_zip, to_json_bytes, to_markdown, to_xlsx
from ..deps import LatestInventoryDep, session_dependency

router = APIRouter(prefix="/export", tags=["export"], dependencies=[session_dependency])


def _content_disposition(filename: str) -> dict[str, str]:
    return {"Content-Disposition": f'attachment; filename="{filename}"'}


@router.get("/json")
async def export_json(inv: LatestInventoryDep) -> Response:
    body = to_json_bytes(inv)
    return Response(
        content=body,
        media_type="application/json",
        headers=_content_disposition("inventory.json"),
    )


@router.get("/markdown")
async def export_markdown(inv: LatestInventoryDep) -> Response:
    body = to_markdown(inv).encode("utf-8")
    return Response(
        content=body,
        media_type="text/markdown; charset=utf-8",
        headers=_content_disposition("inventory.md"),
    )


@router.get("/csv")
async def export_csv(inv: LatestInventoryDep) -> Response:
    body = to_csv_zip(inv)
    return Response(
        content=body,
        media_type="application/zip",
        headers=_content_disposition("inventory.zip"),
    )


@router.get("/xlsx")
async def export_xlsx(inv: LatestInventoryDep) -> Response:
    body = to_xlsx(inv)
    return Response(
        content=body,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=_content_disposition("inventory.xlsx"),
    )
