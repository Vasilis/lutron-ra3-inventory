#!/usr/bin/env python3
"""
Lutron RadioRA3 inventory extractor.

Pairs with a Lutron RA3 processor over LEAP (port 8083 for pairing, 8081 for
data) using the `pylutron-caseta` library, then dumps every available field
(areas, devices, buttons, occupancy groups) to:

  - lutron_inventory.md    (human-readable Markdown report, grouped by area)
  - lutron_inventory.json  (full raw structured dump for programmatic use)

Pairing certs are cached in ./lutron_certs/ next to this script, so you only
have to press the processor button once.

Usage:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install 'pylutron-caseta>=0.28.0'
  python lutron_extract.py --host 192.168.1.184

Optional:
  --host         Processor IP (default: 192.168.1.184)
  --certs-dir    Where to store/load cert files (default: ./lutron_certs)
  --out-dir      Where to write the report files (default: . )
  --force-pair   Re-run the pairing flow even if cert files exist

Verified against pylutron-caseta 0.28.0 (April 2026).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from pylutron_caseta.pairing import async_pair
    from pylutron_caseta.smartbridge import Smartbridge
except ImportError:
    sys.stderr.write(
        "ERROR: pylutron-caseta is not installed.\n"
        "Install it with:  pip install 'pylutron-caseta>=0.28.0'\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------

CERT_FILES = {
    "ca":   "caseta-bridge.crt",
    "cert": "caseta.crt",
    "key":  "caseta.key",
}


def certs_present(certs_dir: Path) -> bool:
    return all((certs_dir / name).exists() for name in CERT_FILES.values())


async def pair_with_processor(host: str, certs_dir: Path) -> None:
    """Run the LEAP pairing flow. Saves three PEM files in certs_dir."""
    certs_dir.mkdir(parents=True, exist_ok=True)

    def ready() -> None:
        print("\n" + "=" * 70)
        print("  PRESS the small black button on the front of the RA3 processor")
        print("  (you have ~30 seconds; the LED will blink while pairing)")
        print("=" * 70 + "\n", flush=True)

    print(f"Contacting {host} on port 8083 to begin pairing...", flush=True)
    data = await async_pair(host, ready)

    for key, filename in CERT_FILES.items():
        path = certs_dir / filename
        path.write_text(data[key])
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass  # Windows / restrictive FS

    version = data.get("version", "unknown")
    print(f"Pairing succeeded. Processor firmware version: {version}")
    print(f"Certificates written to {certs_dir.resolve()}\n")


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

@dataclass
class Inventory:
    host: str
    extracted_at: str
    areas: dict[str, dict[str, Any]]
    devices: dict[str, dict[str, Any]]
    buttons: dict[str, dict[str, Any]]
    occupancy_groups: dict[str, dict[str, Any]]
    scenes: dict[str, dict[str, Any]]  # empty for RA3, included for completeness

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "extracted_at": self.extracted_at,
            "summary": {
                "areas":            len(self.areas),
                "devices":          len(self.devices),
                "buttons":          len(self.buttons),
                "occupancy_groups": len(self.occupancy_groups),
                "scenes":           len(self.scenes),
            },
            "areas":            self.areas,
            "devices":          self.devices,
            "buttons":          self.buttons,
            "occupancy_groups": self.occupancy_groups,
            "scenes":           self.scenes,
        }


async def extract_inventory(host: str, certs_dir: Path) -> Inventory:
    keyfile  = str(certs_dir / CERT_FILES["key"])
    certfile = str(certs_dir / CERT_FILES["cert"])
    ca_certs = str(certs_dir / CERT_FILES["ca"])

    print(f"Connecting to processor at {host}:8081 (LEAP)...", flush=True)
    bridge = Smartbridge.create_tls(host, keyfile, certfile, ca_certs)
    await bridge.connect()
    print("Connected. Reading project data...", flush=True)

    try:
        inv = Inventory(
            host=host,
            extracted_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            areas=dict(bridge.areas or {}),
            devices=dict(bridge.get_devices() or {}),
            buttons=dict(bridge.get_buttons() or {}),
            occupancy_groups=dict(bridge.occupancy_groups or {}),
            scenes=dict(bridge.get_scenes() or {}),  # empty on RA3
        )
    finally:
        await bridge.close()
        print("Disconnected.\n", flush=True)

    return inv


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _fmt_val(v: Any) -> str:
    if v is None or v == "":
        return "_(none)_"
    if isinstance(v, (list, dict)):
        return f"`{json.dumps(v, default=str)}`"
    return str(v)


def _area_path(area_id: str, areas: dict[str, dict[str, Any]]) -> str:
    """Build 'Grandparent > Parent > Self' breadcrumb."""
    parts: list[str] = []
    seen: set[str] = set()
    cur = area_id
    while cur and cur in areas and cur not in seen:
        seen.add(cur)
        parts.append(areas[cur].get("name", cur))
        cur = areas[cur].get("parent_id")
    return " > ".join(reversed(parts)) if parts else "(unassigned)"


def build_markdown(inv: Inventory) -> str:
    out: list[str] = []
    s = inv.to_dict()["summary"]

    out.append(f"# Lutron RadioRA3 Inventory — {inv.host}")
    out.append("")
    out.append(f"_Extracted {inv.extracted_at} via `pylutron-caseta`._")
    out.append("")

    # ----- Summary table -----
    out.append("## Summary")
    out.append("")
    out.append("| Category | Count |")
    out.append("|---|---:|")
    out.append(f"| Areas | {s['areas']} |")
    out.append(f"| Devices (incl. processor & KeypadLEDs) | {s['devices']} |")
    out.append(f"| Buttons | {s['buttons']} |")
    out.append(f"| Occupancy groups | {s['occupancy_groups']} |")
    out.append(f"| Scenes | {s['scenes']} _(RA3 does not expose scenes via LEAP)_ |")
    out.append("")

    # ----- Areas tree -----
    out.append("## Areas")
    out.append("")
    out.append("| ID | Name | Parent | Path |")
    out.append("|---|---|---|---|")
    for aid, a in sorted(inv.areas.items(), key=lambda kv: _area_path(kv[0], inv.areas)):
        out.append(
            f"| `{aid}` | {a.get('name','')} | "
            f"{a.get('parent_id') or '_(root)_'} | "
            f"{_area_path(aid, inv.areas)} |"
        )
    out.append("")

    # ----- Devices grouped by area -----
    out.append("## Devices by Area")
    out.append("")

    # Bucket devices by area id; unassigned go to None bucket
    by_area: dict[str | None, list[tuple[str, dict[str, Any]]]] = {}
    for did, d in inv.devices.items():
        by_area.setdefault(d.get("area"), []).append((did, d))

    # Stable area order: by path, with None last
    sorted_area_ids = sorted(
        [aid for aid in by_area if aid is not None],
        key=lambda aid: _area_path(aid, inv.areas),
    )
    if None in by_area:
        sorted_area_ids.append(None)  # type: ignore[arg-type]

    for aid in sorted_area_ids:
        label = _area_path(aid, inv.areas) if aid else "_(no area — processor / synthetic)_"
        out.append(f"### {label}")
        out.append("")
        out.append("| Device ID | Name | Type | Model | Serial | Zone | Parent | Control Station | Button Groups |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for did, d in sorted(by_area[aid], key=lambda kv: (kv[1].get("type",""), kv[1].get("name",""))):
            out.append(
                "| "
                f"`{did}` | "
                f"{_fmt_val(d.get('name'))} | "
                f"{_fmt_val(d.get('type'))} | "
                f"{_fmt_val(d.get('model'))} | "
                f"{_fmt_val(d.get('serial'))} | "
                f"{_fmt_val(d.get('zone'))} | "
                f"{_fmt_val(d.get('parent_device'))} | "
                f"{_fmt_val(d.get('control_station_name'))} | "
                f"{_fmt_val(d.get('button_groups'))} |"
            )
        out.append("")

    # ----- Buttons -----
    out.append("## Buttons (keypads, picos, etc.)")
    out.append("")
    if not inv.buttons:
        out.append("_No buttons reported._")
        out.append("")
    else:
        # Group buttons by their parent device
        by_parent: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for bid, b in inv.buttons.items():
            by_parent.setdefault(b.get("parent_device", "?"), []).append((bid, b))

        for parent_id, bs in sorted(by_parent.items()):
            parent_dev = inv.devices.get(parent_id, {})
            parent_label = (
                f"{parent_dev.get('name','?')} "
                f"({parent_dev.get('model','?')}, "
                f"area: {_area_path(parent_dev.get('area',''), inv.areas)})"
            )
            out.append(f"### {parent_label} — `{parent_id}`")
            out.append("")
            out.append("| Button ID | # | Group | Button Name | Engraving (name) | Type | Model | Serial | LED |")
            out.append("|---|---:|---|---|---|---|---|---|---|")
            for bid, b in sorted(bs, key=lambda kv: (kv[1].get("button_group",""), kv[1].get("button_number") or 0)):
                out.append(
                    "| "
                    f"`{bid}` | "
                    f"{_fmt_val(b.get('button_number'))} | "
                    f"{_fmt_val(b.get('button_group'))} | "
                    f"{_fmt_val(b.get('button_name'))} | "
                    f"{_fmt_val(b.get('name'))} | "
                    f"{_fmt_val(b.get('type'))} | "
                    f"{_fmt_val(b.get('model'))} | "
                    f"{_fmt_val(b.get('serial'))} | "
                    f"{_fmt_val(b.get('button_led'))} |"
                )
            out.append("")

    # ----- Occupancy groups -----
    out.append("## Occupancy Groups")
    out.append("")
    if not inv.occupancy_groups:
        out.append("_No occupancy groups reported._")
    else:
        out.append("| Group ID | Name | Area | Status | Sensors |")
        out.append("|---|---|---|---|---|")
        for gid, g in sorted(inv.occupancy_groups.items()):
            area_id = g.get("area", "")
            out.append(
                "| "
                f"`{gid}` | "
                f"{_fmt_val(g.get('name') or g.get('device_name'))} | "
                f"{_area_path(area_id, inv.areas)} | "
                f"{_fmt_val(g.get('status'))} | "
                f"{_fmt_val(g.get('sensors'))} |"
            )
    out.append("")

    # ----- Appendix: raw counts caveat -----
    out.append("## Notes & Caveats")
    out.append("")
    out.append(
        "- **Serial numbers**: Some devices (KeypadLEDs, certain keypads) report "
        "`serial` as null. The factory-printed serial is only fully reliable from "
        "the Designer/Essentials project file."
    )
    out.append(
        "- **Scenes**: `pylutron-caseta` does not load scenes on the RA3/HWQS code "
        "path. Scene buttons appear under their parent keypad in the Buttons section."
    )
    out.append(
        "- **Processor itself** is listed as device `1`, type `SmartBridge`/processor."
    )
    out.append(
        "- A full, untruncated dump is in `lutron_inventory.json` next to this report."
    )

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def amain(args: argparse.Namespace) -> int:
    certs_dir = Path(args.certs_dir).expanduser().resolve()
    out_dir   = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.force_pair or not certs_present(certs_dir):
        if args.force_pair:
            print("--force-pair set; ignoring any existing certs.")
        else:
            print(f"No certs found in {certs_dir}; running pairing flow.")
        try:
            await pair_with_processor(args.host, certs_dir)
        except Exception as e:  # noqa: BLE001
            print(f"\nPAIRING FAILED: {e!r}", file=sys.stderr)
            print(
                "\nTroubleshooting:\n"
                "  - Confirm you can reach the processor:  ping 192.168.1.184\n"
                "  - Confirm port 8083 is reachable:       nc -vz 192.168.1.184 8083\n"
                "  - Make sure no other client is mid-pairing.\n"
                "  - Press the processor's physical button when prompted.",
                file=sys.stderr,
            )
            return 2
    else:
        print(f"Using cached certs in {certs_dir}.")

    try:
        inv = await extract_inventory(args.host, certs_dir)
    except Exception as e:  # noqa: BLE001
        print(f"\nEXTRACTION FAILED: {e!r}", file=sys.stderr)
        print(
            "If certs are stale (e.g. processor was factory-reset), re-run with "
            "--force-pair to re-pair.",
            file=sys.stderr,
        )
        return 3

    md_path   = out_dir / "lutron_inventory.md"
    json_path = out_dir / "lutron_inventory.json"

    md_path.write_text(build_markdown(inv))
    json_path.write_text(json.dumps(inv.to_dict(), indent=2, default=str))

    s = inv.to_dict()["summary"]
    print("Done.")
    print(f"  Markdown report : {md_path}")
    print(f"  Raw JSON dump   : {json_path}")
    print(
        f"  Counts          : areas={s['areas']} devices={s['devices']} "
        f"buttons={s['buttons']} occ_groups={s['occupancy_groups']} "
        f"scenes={s['scenes']}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract a Lutron RA3 inventory over LEAP.")
    p.add_argument("--host", default="192.168.1.184", help="Processor IP/hostname")
    p.add_argument("--certs-dir", default="./lutron_certs",
                   help="Where to read/write pairing certificates")
    p.add_argument("--out-dir", default=".",
                   help="Where to write the Markdown + JSON output")
    p.add_argument("--force-pair", action="store_true",
                   help="Re-run pairing even if cached certs exist")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    try:
        rc = asyncio.run(amain(args))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        rc = 130
    sys.exit(rc)


if __name__ == "__main__":
    main()
