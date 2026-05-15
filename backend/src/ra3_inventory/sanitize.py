"""Snapshot sanitization for safe sharing outside the app."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import ProcessorInventory

NULL_KEYS = frozenset({"SerialNumber"})
MAC_KEYS = frozenset({"MACAddress"})
XID_KEYS = frozenset({"XID"})


def _build_area_name_map(data: dict[str, Any]) -> dict[str, str]:
    """Map each real area name to ``Area N`` in deterministic href order."""
    areas = data.get("areas", []) or []
    name_map: dict[str, str] = {}
    for i, area in enumerate(sorted(areas, key=lambda item: item.get("href", "")), start=1):
        old = area.get("Name") or ""
        new = f"Area {i}"
        if old and old != new:
            name_map[old] = new
    return name_map


def sanitize_snapshot_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return a redacted deep copy of one snapshot-shaped dict."""
    sanitized = deepcopy(data)
    sanitized["host"] = "192.0.2.1"

    if isinstance(sanitized.get("processor"), dict):
        sanitized["processor"]["Name"] = "Processor"
    if isinstance(sanitized.get("project"), dict):
        sanitized["project"]["Name"] = "RA3 Inventory Demo Project"

    area_name_map = _build_area_name_map(sanitized)
    sorted_olds = sorted(area_name_map, key=len, reverse=True)

    def redact_str(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        for old in sorted_olds:
            if old and old in value:
                value = value.replace(old, area_name_map[old])
        return value

    def walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                if key == "Name" and isinstance(value, str) and value in area_name_map:
                    obj[key] = area_name_map[value]
                elif key in NULL_KEYS and value is not None:
                    obj[key] = None
                elif key in MAC_KEYS and value:
                    obj[key] = "00:00:00:00:00:00"
                elif key in XID_KEYS and isinstance(value, str):
                    obj[key] = "REDACTED-XID"
                elif isinstance(value, str):
                    obj[key] = redact_str(value)
                elif isinstance(value, list):
                    obj[key] = [walk(item) for item in value]
                elif isinstance(value, dict):
                    obj[key] = walk(value)
            return obj
        if isinstance(obj, list):
            return [walk(item) for item in obj]
        return obj

    return walk(sanitized)


def sanitize_inventory(inventory: ProcessorInventory) -> ProcessorInventory:
    """Return a sanitized copy of ``inventory`` preserving the schema."""
    data = inventory.model_dump(mode="json")
    return ProcessorInventory.model_validate(sanitize_snapshot_data(data))
