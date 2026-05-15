#!/usr/bin/env python3
"""
Sanitize a real Lutron inventory dump for safe use as a public test fixture.

What gets redacted:
  - Area names                       -> "Area 1", "Area 2", ...
  - Device / button / station names  -> area names inside them rewritten
                                        (e.g. "Dining Room_Side Left" -> "Area 1_Side Left")
  - SerialNumber / serial            -> null
  - MACAddress fields                -> "00:00:00:00:00:00"
  - host                             -> "192.0.2.1" (TEST-NET-1)

What's preserved (safe to ship):
  - All hrefs, IDs, zone numbers, button numbers
  - DeviceType, ModelNumber, ControlType, Category, FirmwareImage
  - Structural relationships (parents, areas, button groups)

Modes:
  library : input is lutron_inventory.json (from lutron_extract.py)
  raw     : input is lutron_raw.json       (from lutron_raw_extract.py)

Usage:
  python sanitize_inventory.py lutron_inventory.json fixtures/sample_inventory.json --mode library
  python sanitize_inventory.py lutron_raw.json       fixtures/sample_raw.json       --mode raw
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Library-mode sanitizer
# ---------------------------------------------------------------------------

def sanitize_library(data: dict) -> dict:
    areas = data.get("areas", {})
    devices = data.get("devices", {})
    buttons = data.get("buttons", {})
    occ = data.get("occupancy_groups", {})

    # Stable area-name map: order by area id (string sort) so output is deterministic
    area_name_map: dict[str, str] = {}
    for i, (aid, a) in enumerate(sorted(areas.items()), 1):
        old = a.get("name") or ""
        new = f"Area {i}"
        if old and old != new:
            area_name_map[old] = new
        a["name"] = new

    # Sort by length desc so longer matches don't get partially clobbered
    sorted_olds = sorted(area_name_map.keys(), key=len, reverse=True)

    def redact_str(s: Any) -> Any:
        if not isinstance(s, str):
            return s
        for old in sorted_olds:
            if old and old in s:
                s = s.replace(old, area_name_map[old])
        return s

    for d in devices.values():
        d["name"] = redact_str(d.get("name"))
        d["device_name"] = redact_str(d.get("device_name"))
        if d.get("control_station_name"):
            d["control_station_name"] = redact_str(d["control_station_name"])
        if d.get("serial") is not None:
            d["serial"] = None

    for b in buttons.values():
        b["name"] = redact_str(b.get("name"))
        b["device_name"] = redact_str(b.get("device_name"))
        if b.get("button_name"):
            b["button_name"] = redact_str(b["button_name"])
        if b.get("serial") is not None:
            b["serial"] = None

    for g in occ.values():
        g["name"] = redact_str(g.get("name"))
        g["device_name"] = redact_str(g.get("device_name"))

    if "host" in data:
        data["host"] = "192.0.2.1"
    return data


# ---------------------------------------------------------------------------
# Raw-LEAP-mode sanitizer
# ---------------------------------------------------------------------------

def sanitize_raw(data: dict) -> dict:
    # 1) Find /area body and rebuild area-name map
    area_node = data.get("/area", {}) or {}
    body = area_node.get("body") if isinstance(area_node, dict) else None
    area_list: list = []
    if isinstance(body, dict):
        for v in body.values():
            if isinstance(v, list):
                area_list = v
                break
    elif isinstance(body, list):
        area_list = body

    area_name_map: dict[str, str] = {}
    for i, a in enumerate(area_list, 1):
        if isinstance(a, dict) and a.get("Name"):
            old = a["Name"]
            new = f"Area {i}"
            if old != new:
                area_name_map[old] = new
            a["Name"] = new

    sorted_olds = sorted(area_name_map.keys(), key=len, reverse=True)

    def redact_str(s: Any) -> Any:
        if not isinstance(s, str):
            return s
        for old in sorted_olds:
            if old and old in s:
                s = s.replace(old, area_name_map[old])
        return s

    sensitive_keys_null = {"SerialNumber"}
    sensitive_keys_mac = {"MACAddress"}

    def walk(o: Any) -> Any:
        if isinstance(o, dict):
            for k in list(o.keys()):
                v = o[k]
                if k in sensitive_keys_null and v is not None:
                    o[k] = None
                elif k in sensitive_keys_mac and v:
                    o[k] = "00:00:00:00:00:00"
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Sanitize a Lutron inventory dump.")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument(
        "--mode", choices=("library", "raw"), default="library",
        help="Which schema the input uses (default: library)",
    )
    args = p.parse_args()

    inp = Path(args.input).expanduser()
    out = Path(args.output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(inp.read_text())
    data = sanitize_raw(data) if args.mode == "raw" else sanitize_library(data)

    out.write_text(json.dumps(data, indent=2, default=str))
    print(f"Wrote sanitized fixture: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
