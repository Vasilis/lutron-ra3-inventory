#!/usr/bin/env python3
"""
Pulls the RAW LEAP /device, /zone, and /area responses from a Lutron RA3
processor, bypassing pylutron-caseta's parsing. This exposes fields the
high-level library discards — most importantly `DeviceType` and
`ModelNumber` for shades (Palladiom vs Sivoia vs Triathlon vs Serena, etc.).

Reuses the certs in ./lutron_certs/ produced by lutron_extract.py.

Outputs:
  lutron_raw.json           full raw dump
  lutron_shades_detail.md   shades-only Markdown table with real DeviceType
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from pylutron_caseta.smartbridge import Smartbridge


async def request(bridge: Smartbridge, url: str) -> dict:
    """Send a raw LEAP ReadRequest and return Body as a plain dict."""
    # pylutron-caseta stores the LEAP client at bridge._leap (private but stable).
    resp = await bridge._leap.request("ReadRequest", url)
    # Response.Body can be a dataclass-ish object; coerce to dict.
    body = getattr(resp, "Body", resp)
    if hasattr(body, "__dict__"):
        body = vars(body)
    return body


def coerce(o):
    """Recursively turn dataclass-like objects into JSON-safe dicts."""
    if isinstance(o, dict):
        return {k: coerce(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [coerce(x) for x in o]
    if hasattr(o, "__dict__"):
        return {k: coerce(v) for k, v in vars(o).items() if not k.startswith("_")}
    return o


async def amain(args) -> int:
    certs = Path(args.certs_dir).expanduser().resolve()
    bridge = Smartbridge.create_tls(
        args.host,
        str(certs / "caseta.key"),
        str(certs / "caseta.crt"),
        str(certs / "caseta-bridge.crt"),
    )
    await bridge.connect()
    print(f"Connected to {args.host}; pulling raw LEAP records...")

    raw = {}
    try:
        for url in ("/device", "/zone", "/area"):
            print(f"  GET {url}")
            raw[url] = coerce(await request(bridge, url))
    finally:
        await bridge.close()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lutron_raw.json").write_text(json.dumps(raw, indent=2, default=str))
    print(f"Wrote {out_dir / 'lutron_raw.json'}")

    # ----- Build shades-detail report -----
    devices = []
    body = raw["/device"]
    # Body is usually {"Devices": [ {...}, {...} ]}
    if isinstance(body, dict):
        devices = body.get("Devices") or body.get("DeviceDefinitions") or []
    elif isinstance(body, list):
        devices = body

    area_body = raw["/area"]
    if isinstance(area_body, dict):
        area_list = area_body.get("Areas") or []
    else:
        area_list = area_body or []
    # Build href->name lookup; areas in LEAP use href like "/area/12"
    area_name = {}
    for a in area_list:
        if isinstance(a, dict):
            href = a.get("href") or a.get("Href")
            nm = a.get("Name")
            if href and nm:
                area_name[href] = nm

    shade_types = {
        "PalladiomShade", "PalladiomWireFreeShade",
        "SivoiaQsTriathlonRollerShade", "SivoiaQsTriathlonHoneycombShade",
        "SivoiaQsTriathlonVenetianBlind", "SivoiaQsTriathlonHorizontalSheerBlind",
        "SerenaCellularShade", "SerenaRollerShade", "SerenaHoneycombShade",
        "SerenaTiltOnlyWoodBlind", "SerenaTiltOnlyVenetianBlind",
        "QsWirelessShade", "QsWiredShade",
        "Shade",  # fallback if processor uses the generic label
    }

    rows = []
    for d in devices:
        if not isinstance(d, dict):
            continue
        dtype = d.get("DeviceType") or ""
        if "Shade" in dtype or "Blind" in dtype:
            parent = d.get("AssociatedArea") or {}
            parent_href = parent.get("href") or parent.get("Href") if isinstance(parent, dict) else None
            rows.append({
                "href":         d.get("href") or d.get("Href"),
                "Name":         d.get("Name"),
                "FullyQualifiedName": " > ".join(d.get("FullyQualifiedName") or []) if isinstance(d.get("FullyQualifiedName"), list) else d.get("FullyQualifiedName"),
                "DeviceType":   dtype,
                "ModelNumber":  d.get("ModelNumber"),
                "SerialNumber": d.get("SerialNumber"),
                "Area":         area_name.get(parent_href, parent_href or ""),
                "FirmwareImage": (d.get("FirmwareImage") or {}).get("Firmware", {}).get("DisplayName") if isinstance(d.get("FirmwareImage"), dict) else None,
            })

    md = ["# Lutron Shade Detail (raw LEAP)", "",
          f"_Host: {args.host}_", "",
          "| Name | Area | DeviceType | ModelNumber | SerialNumber | Firmware | href |",
          "|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["Area"] or "", r["Name"] or "")):
        md.append(
            f"| {r['Name'] or ''} | {r['Area'] or ''} | "
            f"`{r['DeviceType']}` | {r['ModelNumber'] or '_(none)_'} | "
            f"{r['SerialNumber'] or '_(none)_'} | {r['FirmwareImage'] or ''} | "
            f"`{r['href'] or ''}` |"
        )
    md.append("")
    md.append(f"_{len(rows)} shade/blind records found._")
    (out_dir / "lutron_shades_detail.md").write_text("\n".join(md) + "\n")
    print(f"Wrote {out_dir / 'lutron_shades_detail.md'}  ({len(rows)} shades)")

    return 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="192.168.1.184")
    p.add_argument("--certs-dir", default="./lutron_certs")
    p.add_argument("--out-dir", default=".")
    args = p.parse_args()
    sys.exit(asyncio.run(amain(args)))


if __name__ == "__main__":
    main()
