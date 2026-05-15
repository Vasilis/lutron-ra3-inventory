"""Area model and tree-path helpers."""

from __future__ import annotations

from .base import HrefRef, RA3Resource


class Area(RA3Resource):
    """``/area/{id}`` — a named room or scope."""

    Name: str | None = None
    Parent: HrefRef | None = None
    """Parent area, or None for the root."""

    OccupancyDetectorIds: list[int] | None = None
    LoadShedding: dict | None = None
    AssociatedZones: list[HrefRef] | None = None
    AssociatedControlStations: list[HrefRef] | None = None


def area_path(href: str | None, areas: dict[str, Area]) -> str:
    """Resolve an area href to its ' > '-joined parent chain.

    Cycle-safe: returns the partial path if a cycle is detected.
    """
    if href is None:
        return "(unassigned)"
    parts: list[str] = []
    seen: set[str] = set()
    cur: str | None = href
    while cur and cur in areas and cur not in seen:
        seen.add(cur)
        a = areas[cur]
        parts.append(a.Name or "?")
        cur = a.Parent.href if a.Parent is not None else None
    return " > ".join(reversed(parts)) if parts else "(unassigned)"
