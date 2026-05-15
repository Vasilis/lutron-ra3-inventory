#!/usr/bin/env python3
"""Sanitize a ProcessorInventory snapshot for safe public sharing.

Adapted from ``docs/legacy/sanitize_inventory.py`` (raw-LEAP mode) to operate
on the new app's snapshot schema. Redacts:

- ``host`` → ``"192.0.2.1"`` (TEST-NET-1 range)
- ``processor.SerialNumber`` and all device ``SerialNumber``s → ``null``
- ``NetworkInterface.MACAddress`` → ``"00:00:00:00:00:00"``
- Area names → ``Area 1``, ``Area 2``, ... in deterministic order, and every
  occurrence of an original area name inside any other string (device names,
  control-station names, zone names) is rewritten to match.
- ``processor.Name`` and ``project.Name`` → generic placeholders
- ``XID`` opaque IDs → ``"REDACTED-XID"``

What is **preserved**:

- All ``href`` paths and numeric IDs (load-bearing for the schema)
- ``DeviceType``, ``ModelNumber``, ``ControlType``, ``Category``, firmware
  version strings
- Structural relationships (Parent, AssociatedArea, ButtonGroups, LinkNodes)
- Button engravings, zone names that don't embed area names

Usage::

    python scripts/sanitize-snapshot.py path/to/snapshot.json examples/sanitized-snapshot.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

NULL_KEYS = frozenset({"SerialNumber"})
MAC_KEYS = frozenset({"MACAddress"})
XID_KEYS = frozenset({"XID"})


def _build_area_name_map(data: dict) -> dict[str, str]:
    """Map each real area name to ``Area N`` (deterministic by href)."""
    areas = data.get("areas", []) or []
    name_map: dict[str, str] = {}
    for i, a in enumerate(sorted(areas, key=lambda x: x.get("href", "")), start=1):
        old = a.get("Name") or ""
        new = f"Area {i}"
        if old and old != new:
            name_map[old] = new
    return name_map


def sanitize_snapshot(data: dict) -> dict:
    """Mutate ``data`` in place to redact identifiers; return it."""
    # 1. host
    data["host"] = "192.0.2.1"

    # 2. processor + project names
    if "processor" in data and isinstance(data["processor"], dict):
        data["processor"]["Name"] = "Processor"
    if "project" in data and isinstance(data["project"], dict):
        data["project"]["Name"] = "RA3 Inventory Demo Project"

    # 3. area-name map (longest first so substrings don't collide)
    area_name_map = _build_area_name_map(data)
    sorted_olds = sorted(area_name_map.keys(), key=len, reverse=True)

    def redact_str(s: Any) -> Any:
        if not isinstance(s, str):
            return s
        for old in sorted_olds:
            if old and old in s:
                s = s.replace(old, area_name_map[old])
        return s

    def walk(o: Any) -> Any:
        if isinstance(o, dict):
            for k in list(o.keys()):
                v = o[k]
                if k == "Name" and isinstance(v, str) and v in area_name_map:
                    o[k] = area_name_map[v]
                elif k in NULL_KEYS and v is not None:
                    o[k] = None
                elif k in MAC_KEYS and v:
                    o[k] = "00:00:00:00:00:00"
                elif k in XID_KEYS and isinstance(v, str):
                    o[k] = "REDACTED-XID"
                elif isinstance(v, str):
                    o[k] = redact_str(v)
                elif isinstance(v, list):
                    o[k] = [walk(x) for x in v]
                elif isinstance(v, dict):
                    o[k] = walk(v)
            return o
        if isinstance(o, list):
            return [walk(x) for x in o]
        return o

    return walk(data)


def main() -> int:
    p = argparse.ArgumentParser(description="Sanitize a ProcessorInventory snapshot.")
    p.add_argument("input", help="snapshot JSON file")
    p.add_argument("output", help="output path (will be created)")
    args = p.parse_args()

    inp = Path(args.input).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(inp.read_text())
    sanitize_snapshot(data)
    out.write_text(json.dumps(data, indent=2, default=str))
    print(f"Wrote sanitized snapshot: {out}")

    # Quick round-trip test
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))
    from ra3_inventory.models import ProcessorInventory  # noqa: E402

    inv = ProcessorInventory.model_validate(data)
    print(
        f"  schema_version={inv.schema_version} "
        f"areas={len(inv.areas)} devices={len(inv.devices)} "
        f"zones={len(inv.zones)} buttons={sum(len(bg.Buttons or []) for bgs in inv.button_group_expansions.values() for bg in bgs)} "
        f"PMs={len(inv.programming_models)} presets={len(inv.presets)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
