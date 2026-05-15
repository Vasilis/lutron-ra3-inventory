#!/usr/bin/env python3
"""
Comprehensive raw-LEAP extractor for Lutron RadioRA3 (and HWQS) processors.

`pylutron-caseta` is used ONLY for the TLS handshake and LEAP wire framing.
Every field is read raw from the processor so we preserve information the
high-level library throws away — DeviceType (PalladiomShade vs SivoiaQS vs
WallDimmer vs SunnataKeypad...), ModelNumber, SerialNumber, FirmwareImage,
ButtonGroups, ProgrammingModel + Preset/Assignment graph, timeclock rules,
etc.

This script supersedes the older `lutron_extract.py` and `lutron_raw_devices.py`.

Endpoints hit (RA3-specific path):
  /project                              project metadata + timeclock href
  /server, /server/1, /server/1/status/ping   server / firmware
  /device?where=IsThisDevice:true       the processor itself
  /device?where=IsThisDevice:false      all other devices (bare /device 204s on RA3)
  /area                                 area tree
  /zone                                 zones (loads)
  /controlstation                       physical keypad gangs
  /buttongroup, /button, /led           flat button/LED lists
  /virtualbutton, /areascene            scenes / timeclock virtual buttons
  /occupancygroup                       (mostly empty on RA3 — kept for completeness)
  /project/timeclockeventrules          timeclock schedule

Plus, for every keypad-like device:
  /device/{id}/buttongroup/expanded     inline buttons + ProgrammingModel hrefs

And every ProgrammingModel + Preset referenced from those buttons is
fetched, so the report can show "Button 1 -> dim zone X to 80%" type
mappings.

Outputs:
  lutron_raw.json              full raw dump of every endpoint hit
  lutron_inventory_raw.md      structured Markdown report
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from pylutron_caseta.smartbridge import Smartbridge
except ImportError:
    sys.stderr.write(
        "ERROR: pylutron-caseta is not installed.\n"
        "  pip install 'pylutron-caseta>=0.26.0'  (0.28+ recommended on Python 3.10+)\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Endpoint catalogue
# ---------------------------------------------------------------------------

TOPLEVEL_ENDPOINTS = [
    "/project",
    "/server",
    "/server/1",
    "/server/1/status/ping",
    "/server/2/id",                 # secondary processor (404 on single-proc RA3 is fine)
    "/area",
    "/area/status",                 # per-area occupancy + current scene
    "/zone",
    "/controlstation",
    "/buttongroup",
    "/button",
    "/led",
    "/virtualbutton",
    "/areascene",
    "/occupancygroup",
    "/project/timeclockeventrules",
    "/system/away/1/status",        # Smart Away state
    "/curve/1",                     # dimming curve (referenced by WarmDim commands)
]

# Bare /device returns 204 on RA3; you must use ?where=IsThisDevice:bool.
DEVICE_ENDPOINTS = [
    "/device?where=IsThisDevice:true",
    "/device?where=IsThisDevice:false",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _coerce(o: Any) -> Any:
    """Recursively turn dataclass-like Response/Body objects into plain JSON."""
    if isinstance(o, dict):
        return {k: _coerce(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_coerce(x) for x in o]
    if hasattr(o, "__dict__"):
        return {k: _coerce(v) for k, v in vars(o).items() if not k.startswith("_")}
    return o


async def leap_read(bridge: Smartbridge, url: str) -> dict[str, Any]:
    """Send a raw LEAP ReadRequest. Returns {status, body, error}."""
    try:
        resp = await bridge._leap.request("ReadRequest", url)
    except Exception as e:  # noqa: BLE001
        return {"status": None, "body": None, "error": repr(e)}
    body = _coerce(getattr(resp, "Body", None))
    header = _coerce(getattr(resp, "Header", {})) or {}
    status = header.get("StatusCode") if isinstance(header, dict) else None
    return {"status": status, "body": body, "error": None}


def list_from_body(body: Any) -> list:
    """LEAP wraps collections as {'Devices': [...]} etc. Find the list."""
    if isinstance(body, list):
        return body
    if not isinstance(body, dict):
        return []
    for v in body.values():
        if isinstance(v, list):
            return v
    return []


def first_obj_from_body(body: Any) -> dict | None:
    """For 'OneXxxDefinition' responses, return the inner dict."""
    if not isinstance(body, dict):
        return None
    for v in body.values():
        if isinstance(v, dict):
            return v
    return body


def _href_id(href: str | None) -> str:
    return (href or "").rsplit("/", 1)[-1] or ""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

async def extract(args: argparse.Namespace) -> dict[str, Any]:
    certs = Path(args.certs_dir).expanduser().resolve()
    bridge = Smartbridge.create_tls(
        args.host,
        str(certs / "caseta.key"),
        str(certs / "caseta.crt"),
        str(certs / "caseta-bridge.crt"),
    )
    print(f"Connecting to {args.host}...", flush=True)
    await bridge.connect()
    print("Connected. Pulling raw LEAP data...\n", flush=True)

    raw: dict[str, Any] = {}
    try:
        # 1) All top-level endpoints + device queries
        for url in TOPLEVEL_ENDPOINTS + DEVICE_ENDPOINTS:
            r = await leap_read(bridge, url)
            raw[url] = r
            count = len(list_from_body(r["body"])) if r["body"] is not None else 0
            note = f"err={r['error']!r}" if r["error"] else f"items={count}"
            print(f"  {url:55s} -> {r['status']!s:4s}  {note}")

        # 2) For each device that has ButtonGroups, fetch the expanded form.
        device_list = list_from_body(raw["/device?where=IsThisDevice:false"]["body"])
        bg_expanded: dict[str, dict[str, Any]] = {}
        keypad_count = 0
        for d in device_list:
            if not isinstance(d, dict):
                continue
            if not d.get("ButtonGroups"):
                continue
            href = d.get("href")
            if not href:
                continue
            url = f"{href}/buttongroup/expanded"
            r = await leap_read(bridge, url)
            bg_expanded[href] = r
            keypad_count += 1
        raw["__buttongroup_expanded__"] = bg_expanded
        print(f"\n  Pulled buttongroup/expanded for {keypad_count} keypad-like devices")

        # 3) Resolve ProgrammingModel hrefs referenced in expanded button groups
        pm_hrefs: set[str] = set()
        for r in bg_expanded.values():
            for bg in list_from_body(r["body"]):
                if not isinstance(bg, dict):
                    continue
                for btn in bg.get("Buttons") or []:
                    pm = btn.get("ProgrammingModel") if isinstance(btn, dict) else None
                    if isinstance(pm, dict) and pm.get("href"):
                        pm_hrefs.add(pm["href"])
        pms: dict[str, dict[str, Any]] = {}
        for href in sorted(pm_hrefs):
            pms[href] = await leap_read(bridge, href)
        raw["__programmingmodels__"] = pms
        print(f"  Pulled {len(pms)} programming models")

        # 4) Resolve every Preset referenced by those programming models
        preset_hrefs: set[str] = set()
        for r in pms.values():
            obj = first_obj_from_body(r["body"])
            if not isinstance(obj, dict):
                continue
            for k in (
                "PressOnPresetAssignments",
                "ReleaseOnPresetAssignments",
                "DoubleTapOnPresetAssignments",
                "HoldOnPresetAssignments",
            ):
                for a in obj.get(k, []) or []:
                    if isinstance(a, dict) and a.get("href"):
                        preset_hrefs.add(a["href"])
        presets: dict[str, dict[str, Any]] = {}
        for href in sorted(preset_hrefs):
            presets[href] = await leap_read(bridge, href)
        raw["__presets__"] = presets
        print(f"  Pulled {len(presets)} presets")
    finally:
        await bridge.close()
        print("\nDisconnected.\n", flush=True)

    return raw


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def build_indices(raw):
    areas, devices, zones, buttons, leds, vbuttons, scenes = {}, {}, {}, {}, {}, {}, {}

    for a in list_from_body(raw.get("/area", {}).get("body")):
        if isinstance(a, dict) and a.get("href"):
            areas[a["href"]] = a
    for url in DEVICE_ENDPOINTS:
        for d in list_from_body(raw.get(url, {}).get("body")):
            if isinstance(d, dict) and d.get("href"):
                devices[d["href"]] = d
    for z in list_from_body(raw.get("/zone", {}).get("body")):
        if isinstance(z, dict) and z.get("href"):
            zones[z["href"]] = z
    for b in list_from_body(raw.get("/button", {}).get("body")):
        if isinstance(b, dict) and b.get("href"):
            buttons[b["href"]] = b
    for l in list_from_body(raw.get("/led", {}).get("body")):
        if isinstance(l, dict) and l.get("href"):
            leds[l["href"]] = l
    for v in list_from_body(raw.get("/virtualbutton", {}).get("body")):
        if isinstance(v, dict) and v.get("href"):
            vbuttons[v["href"]] = v
    for s in list_from_body(raw.get("/areascene", {}).get("body")):
        if isinstance(s, dict) and s.get("href"):
            scenes[s["href"]] = s
    return {
        "areas": areas, "devices": devices, "zones": zones,
        "buttons": buttons, "leds": leds,
        "vbuttons": vbuttons, "scenes": scenes,
    }


def area_path(href, areas):
    parts, seen, cur = [], set(), href
    while cur and cur in areas and cur not in seen:
        seen.add(cur)
        a = areas[cur]
        parts.append(a.get("Name") or "?")
        parent = a.get("Parent") or {}
        cur = parent.get("href") if isinstance(parent, dict) else None
    return " > ".join(reversed(parts)) if parts else "(unassigned)"


# ---------------------------------------------------------------------------
# Programming model → action resolver
# ---------------------------------------------------------------------------

def resolve_button_action(btn, pms, presets, zones):
    pm_ref = btn.get("ProgrammingModel") if isinstance(btn, dict) else None
    if not isinstance(pm_ref, dict) or not pm_ref.get("href"):
        return "_(no PM)_"
    pm_resp = pms.get(pm_ref["href"])
    if not pm_resp:
        return f"_(PM {pm_ref['href']} not pulled)_"
    pm_obj = first_obj_from_body(pm_resp.get("body"))
    if not isinstance(pm_obj, dict):
        return "_(no PM body)_"

    pm_type = pm_obj.get("ProgrammingModelType", "?")
    bits = []
    action_keys = [
        ("PressOnPresetAssignments",      "press"),
        ("ReleaseOnPresetAssignments",    "release"),
        ("DoubleTapOnPresetAssignments",  "double-tap"),
        ("HoldOnPresetAssignments",       "hold"),
    ]
    asn_keys = [
        ("DimmedLevelAssignments",   "dim",    "Level"),
        ("FanSpeedAssignments",      "fan",    "FanSpeed"),
        ("TiltAssignments",          "tilt",   "Tilt"),
        ("SwitchedLevelAssignments", "switch", "SwitchedLevel"),
    ]
    for act_key, act_label in action_keys:
        for a in pm_obj.get(act_key, []) or []:
            if not isinstance(a, dict):
                continue
            pdata = first_obj_from_body((presets.get(a.get("href")) or {}).get("body"))
            if not isinstance(pdata, dict):
                continue
            for asn_key, asn_label, lvl_field in asn_keys:
                for asn in pdata.get(asn_key, []) or []:
                    if not isinstance(asn, dict):
                        continue
                    aobj = asn.get("AssignableObject") or {}
                    zref = aobj.get("href") if isinstance(aobj, dict) else None
                    zname = "?"
                    if zref and zref in zones:
                        zname = zones[zref].get("Name", zref)
                    elif zref:
                        zname = zref
                    lvl = asn.get(lvl_field) or asn.get("Level")
                    bits.append(f"{act_label}:{asn_label}({zname})={lvl}")
    if not bits:
        return f"`{pm_type}` _(no assignments)_"
    return f"`{pm_type}` " + " · ".join(bits)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def build_inventory_md(raw, host):
    idx = build_indices(raw)
    areas, devices, zones, buttons, leds = idx["areas"], idx["devices"], idx["zones"], idx["buttons"], idx["leds"]
    bg_expanded = raw.get("__buttongroup_expanded__", {})
    pms = raw.get("__programmingmodels__", {})
    presets = raw.get("__presets__", {})

    project = first_obj_from_body(raw.get("/project", {}).get("body")) or {}
    proc_list = list_from_body(raw.get("/device?where=IsThisDevice:true", {}).get("body"))
    processor = proc_list[0] if proc_list and isinstance(proc_list[0], dict) else None

    md: list[str] = []
    md.append(f"# Lutron Inventory (raw LEAP) — {host}")
    md.append("")
    if project:
        md.append(f"**Project:** {project.get('Name','?')}  ")
        md.append(f"**ProductType:** `{project.get('ProductType','?')}`  ")
        md.append(f"**Project Modified:** {project.get('ProjectModifiedTimestamp','?')}")
        md.append("")

    # Processor
    if processor:
        fw_obj = processor.get("FirmwareImage") or {}
        fw_dn = "?"
        if isinstance(fw_obj, dict):
            f = fw_obj.get("Firmware") or {}
            if isinstance(f, dict):
                fw_dn = f.get("DisplayName", "?")
        nets = processor.get("NetworkInterfaces") or []
        mac = nets[0].get("MACAddress") if nets and isinstance(nets[0], dict) else "?"
        md.append("## Processor")
        md.append("")
        md.append("| Field | Value |")
        md.append("|---|---|")
        md.append(f"| href | `{processor.get('href','?')}` |")
        md.append(f"| Name | {processor.get('Name','?')} |")
        md.append(f"| DeviceType | `{processor.get('DeviceType','?')}` |")
        md.append(f"| ModelNumber | {processor.get('ModelNumber','?')} |")
        md.append(f"| SerialNumber | {processor.get('SerialNumber','?')} |")
        md.append(f"| Firmware | {fw_dn} |")
        md.append(f"| MAC | {mac} |")
        md.append(f"| AddressedState | {processor.get('AddressedState','?')} |")
        md.append("")

    # Summary
    md.append("## Summary")
    md.append("")
    md.append("| Category | Count |")
    md.append("|---|---:|")
    md.append(f"| Areas | {len(areas)} |")
    md.append(f"| Devices (excl. processor) | {len(devices)} |")
    md.append(f"| Zones | {len(zones)} |")
    md.append(f"| Buttons | {len(buttons)} |")
    md.append(f"| LEDs | {len(leds)} |")
    md.append(f"| Virtual buttons | {len(idx['vbuttons'])} |")
    md.append(f"| Area scenes | {len(idx['scenes'])} |")
    md.append(f"| ProgrammingModels resolved | {len(pms)} |")
    md.append(f"| Presets resolved | {len(presets)} |")
    md.append("")

    # Device-type counts (this is the slim view your AI agent probably wants)
    type_counts: dict[tuple[str, str], int] = defaultdict(int)
    for d in devices.values():
        type_counts[(d.get("DeviceType", "?"), d.get("ModelNumber") or "_(none)_")] += 1
    md.append("## Device Type × Model")
    md.append("")
    md.append("| Count | DeviceType | ModelNumber |")
    md.append("|---:|---|---|")
    for (t, m), n in sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        md.append(f"| {n} | `{t}` | {m} |")
    md.append("")

    # Areas
    md.append("## Areas")
    md.append("")
    md.append("| href | Name | Parent | Full path |")
    md.append("|---|---|---|---|")
    for href, a in sorted(areas.items(), key=lambda kv: area_path(kv[0], areas)):
        parent = a.get("Parent") or {}
        phref = parent.get("href") if isinstance(parent, dict) else None
        md.append(f"| `{href}` | {a.get('Name','?')} | `{phref or 'root'}` | {area_path(href, areas)} |")
    md.append("")

    # Devices by area, full fields
    md.append("## Devices by Area (full fields)")
    md.append("")
    by_area: dict[str | None, list[tuple[str, dict]]] = defaultdict(list)
    for href, d in devices.items():
        aa = d.get("AssociatedArea")
        ahref = aa.get("href") if isinstance(aa, dict) else None
        by_area[ahref].append((href, d))

    for ahref in sorted(by_area.keys(),
                        key=lambda h: (area_path(h, areas) if h else "zzz")):
        label = area_path(ahref, areas) if ahref else "_(unassigned)_"
        md.append(f"### {label}")
        md.append("")
        md.append("| href | Name | DeviceType | ModelNumber | SerialNumber | "
                  "Firmware | Addressed | LocalZones | ButtonGroups |")
        md.append("|---|---|---|---|---|---|---|---|---|")
        rows = sorted(by_area[ahref],
                      key=lambda x: (x[1].get("DeviceType",""), x[1].get("Name","")))
        for dhref, d in rows:
            fw_obj = d.get("FirmwareImage") or {}
            fw = "_(none)_"
            if isinstance(fw_obj, dict):
                f = fw_obj.get("Firmware") or {}
                if isinstance(f, dict):
                    fw = f.get("DisplayName", "_(none)_")
            lzs = d.get("LocalZones") or []
            lz_str = ", ".join(_href_id(z.get("href")) for z in lzs if isinstance(z, dict)) or "_(none)_"
            bgs = d.get("ButtonGroups") or []
            bg_str = ", ".join(_href_id(b.get("href")) for b in bgs if isinstance(b, dict)) or "_(none)_"
            md.append(
                f"| `{dhref}` | {d.get('Name','?')} | `{d.get('DeviceType','?')}` | "
                f"{d.get('ModelNumber') or '_(none)_'} | {d.get('SerialNumber') or '_(none)_'} | "
                f"{fw} | {d.get('AddressedState','?')} | {lz_str} | {bg_str} |"
            )
        md.append("")

    # Zones
    md.append("## Zones")
    md.append("")
    md.append("| href | Name | ControlType | Category | Device |")
    md.append("|---|---|---|---|---|")
    for zhref, z in sorted(zones.items(), key=lambda x: x[1].get("Name","")):
        cat = z.get("Category") or {}
        cat_str = (f"{cat.get('Type','?')}/{cat.get('SubType','?')}"
                   if isinstance(cat, dict) else "?")
        dev = z.get("Device") or z.get("AssociatedArea") or {}
        dev_href = dev.get("href") if isinstance(dev, dict) else None
        md.append(f"| `{zhref}` | {z.get('Name','?')} | {z.get('ControlType','?')} | "
                  f"{cat_str} | `{dev_href or ''}` |")
    md.append("")

    # Keypads
    md.append("## Keypads — Buttons & Programming")
    md.append("")
    md.append("_For each keypad/pico/remote: every button with its engraving and what it does._")
    md.append("")
    if not bg_expanded:
        md.append("_No keypad button data captured._")
        md.append("")
    for dhref, r in sorted(bg_expanded.items()):
        d = devices.get(dhref) or {}
        ahref = (d.get("AssociatedArea") or {}).get("href") if isinstance(d.get("AssociatedArea"), dict) else None
        md.append(f"### {d.get('Name','?')} — `{dhref}`")
        md.append(f"_{d.get('DeviceType','?')} {d.get('ModelNumber','') or ''} · "
                  f"Area: {area_path(ahref, areas) if ahref else '?'} · "
                  f"SN: {d.get('SerialNumber','?')}_")
        md.append("")
        md.append("| # | Engraving / Name | ButtonType | Action |")
        md.append("|---:|---|---|---|")
        for bg in list_from_body(r.get("body")):
            if not isinstance(bg, dict):
                continue
            for btn in bg.get("Buttons") or []:
                if not isinstance(btn, dict):
                    continue
                eng = btn.get("Engraving") or {}
                eng_text = eng.get("Text") if isinstance(eng, dict) else None
                action = resolve_button_action(btn, pms, presets, zones)
                md.append(
                    f"| {btn.get('ButtonNumber','?')} | "
                    f"{eng_text or btn.get('Name','')} | "
                    f"`{btn.get('ButtonType','?')}` | "
                    f"{action} |"
                )
        md.append("")

    # Virtual buttons
    if idx["vbuttons"]:
        md.append("## Virtual Buttons (timeclock / scene targets)")
        md.append("")
        md.append("| href | Name | Category | ProgrammingModel |")
        md.append("|---|---|---|---|")
        for href, v in sorted(idx["vbuttons"].items()):
            cat = v.get("Category") or {}
            cat_str = cat.get("Type","?") if isinstance(cat, dict) else ""
            pm = v.get("ProgrammingModel") or {}
            pmhref = pm.get("href") if isinstance(pm, dict) else None
            md.append(f"| `{href}` | {v.get('Name','?')} | {cat_str} | `{pmhref or ''}` |")
        md.append("")

    # Area scenes
    if idx["scenes"]:
        md.append("## Area Scenes")
        md.append("")
        md.append("| href | Name | Area | ProgrammingModel |")
        md.append("|---|---|---|---|")
        for href, s in sorted(idx["scenes"].items()):
            pa = s.get("Parent") or {}
            phref = pa.get("href") if isinstance(pa, dict) else None
            pm = s.get("ProgrammingModel") or {}
            pmhref = pm.get("href") if isinstance(pm, dict) else None
            md.append(f"| `{href}` | {s.get('Name','?')} | "
                      f"{area_path(phref, areas) if phref else '?'} | `{pmhref or ''}` |")
        md.append("")

    # Timeclock
    tc_body = raw.get("/project/timeclockeventrules", {}).get("body")
    tc_list = list_from_body(tc_body) if tc_body else []
    if tc_list:
        md.append("## Timeclock Event Rules")
        md.append("")
        md.append("| href | Name | Enabled | Days | TimeReference |")
        md.append("|---|---|---|---|---|")
        for t in tc_list:
            if not isinstance(t, dict):
                continue
            md.append(f"| `{t.get('href')}` | {t.get('Name','?')} | "
                      f"{t.get('Enabled','?')} | {t.get('DaysOfWeek','?')} | "
                      f"{t.get('TimeReference','?')} |")
        md.append("")

    # Footer
    md.append("## How to dig deeper")
    md.append("")
    md.append("The full raw response for every endpoint and per-device expansion "
              "is in `lutron_raw.json`. Useful jq one-liners:")
    md.append("")
    md.append("```bash")
    md.append("# all shades with model/serial")
    md.append("jq '.[\"/device?where=IsThisDevice:false\"].body.Devices[] "
              "| select(.DeviceType|test(\"Shade|Blind\")) "
              "| {href,Name,DeviceType,ModelNumber,SerialNumber}' lutron_raw.json")
    md.append("")
    md.append("# every button with its resolved programming model")
    md.append("jq '.__buttongroup_expanded__' lutron_raw.json")
    md.append("```")
    return "\n".join(md) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def amain(args: argparse.Namespace) -> int:
    try:
        raw = await extract(args)
    except Exception as e:  # noqa: BLE001
        print(f"\nEXTRACTION FAILED: {e!r}", file=sys.stderr)
        print("If certs are stale (factory-reset, revoked), re-pair with "
              "lutron_extract.py --force-pair.", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "lutron_raw.json"
    json_path.write_text(json.dumps(raw, indent=2, default=str))

    md_path = out_dir / "lutron_inventory_raw.md"
    md_path.write_text(build_inventory_md(raw, args.host))

    print("Done.")
    print(f"  Raw JSON   : {json_path}")
    print(f"  Inventory  : {md_path}")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Raw LEAP extractor for Lutron RA3/HWQS")
    p.add_argument("--host", default="192.168.1.184")
    p.add_argument("--certs-dir", default="./lutron_certs",
                   help="Reuses the certs created by lutron_extract.py")
    p.add_argument("--out-dir", default=".",
                   help="Where to write lutron_raw.json + lutron_inventory_raw.md")
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
