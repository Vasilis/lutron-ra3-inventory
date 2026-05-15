"""Markdown report export — typed re-implementation of the legacy script's report.

Ported from ``build_inventory_md()`` in ``docs/legacy/lutron_raw_extract.py``.
Operates on a typed ``ProcessorInventory`` instead of raw dicts, but produces
a Markdown structure intentionally close to the legacy output so the visual
diff for users moving from the standalone script is minimal.
"""

from __future__ import annotations

from collections import defaultdict

from ..models import (
    Area,
    Button,
    ButtonGroup,
    Device,
    ProcessorInventory,
    Zone,
    area_path,
)
from ._resolver import resolve_button_action


def _firmware_display(d: Device) -> str:
    fw = d.FirmwareImage
    if fw is None or fw.Firmware is None or fw.Firmware.DisplayName is None:
        return "_(none)_"
    return fw.Firmware.DisplayName


def _href_id(href: str | None) -> str:
    return (href or "").rsplit("/", 1)[-1] or ""


def to_markdown(inv: ProcessorInventory) -> str:
    """Build a human-readable Markdown report for one ProcessorInventory."""
    areas_by_href: dict[str, Area] = {a.href: a for a in inv.areas}
    zones_by_href: dict[str, Zone] = {z.href: z for z in inv.zones}

    lines: list[str] = []
    lines.append(f"# Lutron Inventory — {inv.host}")
    lines.append("")
    lines.append(f"**Project:** {inv.project.Name or '?'}  ")
    lines.append(f"**ProductType:** `{inv.project.ProductType or '?'}`  ")
    if inv.project.ProjectModifiedTimestamp:
        lines.append(f"**Project Modified:** {inv.project.ProjectModifiedTimestamp}  ")
    lines.append(f"**Extracted at:** {inv.extracted_at.isoformat()}  ")
    lines.append(f"**Schema:** v{inv.schema_version}")
    if inv.partial:
        lines.append("")
        lines.append("> **Note:** this snapshot is marked `partial=true` — the processor's "
                     "project was modified during extraction.")
    lines.append("")

    # Processor
    p = inv.processor
    mac = ""
    if p.NetworkInterfaces:
        first = p.NetworkInterfaces[0]
        mac = first.MACAddress or ""
    lines.append("## Processor")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| href | `{p.href}` |")
    lines.append(f"| Name | {p.Name or '?'} |")
    lines.append(f"| DeviceType | `{p.DeviceType}` |")
    lines.append(f"| ModelNumber | {p.ModelNumber or '?'} |")
    lines.append(f"| SerialNumber | {p.SerialNumber or '?'} |")
    lines.append(f"| Firmware | {_firmware_display(p)} |")
    lines.append(f"| MAC | {mac or '?'} |")
    lines.append(f"| AddressedState | {p.AddressedState or '?'} |")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|---|---:|")
    lines.append(f"| Areas | {len(inv.areas)} |")
    lines.append(f"| Devices (excl. processor) | {len(inv.devices)} |")
    lines.append(f"| Zones | {len(inv.zones)} |")
    lines.append(f"| Buttons | {len(inv.buttons)} |")
    lines.append(f"| LEDs | {len(inv.leds)} |")
    lines.append(f"| Virtual buttons | {len(inv.virtual_buttons)} |")
    lines.append(f"| Area scenes | {len(inv.area_scenes)} |")
    lines.append(f"| ProgrammingModels resolved | {len(inv.programming_models)} |")
    lines.append(f"| Presets resolved | {len(inv.presets)} |")
    lines.append("")

    # DeviceType × Model counts
    type_counts: dict[tuple[str, str], int] = defaultdict(int)
    for d in inv.devices:
        type_counts[(d.DeviceType, d.ModelNumber or "_(none)_")] += 1
    lines.append("## Device Type × Model")
    lines.append("")
    lines.append("| Count | DeviceType | ModelNumber |")
    lines.append("|---:|---|---|")
    for (t, m), n in sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| {n} | `{t}` | {m} |")
    lines.append("")

    # Areas
    lines.append("## Areas")
    lines.append("")
    lines.append("| href | Name | Parent | Full path |")
    lines.append("|---|---|---|---|")
    sorted_areas = sorted(inv.areas, key=lambda a: area_path(a.href, areas_by_href))
    for a in sorted_areas:
        phref = a.Parent.href if a.Parent is not None else None
        lines.append(
            f"| `{a.href}` | {a.Name or '?'} | `{phref or 'root'}` | "
            f"{area_path(a.href, areas_by_href)} |"
        )
    lines.append("")

    # Devices by area
    by_area: dict[str | None, list[Device]] = defaultdict(list)
    for d in inv.devices:
        ahref = d.AssociatedArea.href if d.AssociatedArea is not None else None
        by_area[ahref].append(d)

    lines.append("## Devices by Area (full fields)")
    lines.append("")
    for ahref in sorted(by_area.keys(), key=lambda h: area_path(h, areas_by_href) if h else "zzz"):
        label = area_path(ahref, areas_by_href) if ahref else "_(unassigned)_"
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| href | Name | DeviceType | ModelNumber | SerialNumber | "
                     "Firmware | Addressed | LocalZones | ButtonGroups |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for d in sorted(by_area[ahref], key=lambda x: (x.DeviceType, x.Name or "")):
            lz = ", ".join(_href_id(r.href) for r in d.LocalZones) or "_(none)_"
            bg = ", ".join(_href_id(r.href) for r in d.ButtonGroups) or "_(none)_"
            lines.append(
                f"| `{d.href}` | {d.Name or '?'} | `{d.DeviceType}` | "
                f"{d.ModelNumber or '_(none)_'} | {d.SerialNumber or '_(none)_'} | "
                f"{_firmware_display(d)} | {d.AddressedState or '?'} | {lz} | {bg} |"
            )
        lines.append("")

    # Zones
    lines.append("## Zones")
    lines.append("")
    lines.append("| href | Name | ControlType | Category | Device |")
    lines.append("|---|---|---|---|---|")
    for z in sorted(inv.zones, key=lambda z: z.Name or ""):
        cat = ""
        if z.Category is not None:
            cat = f"{z.Category.Type or '?'}/{z.Category.SubType or '?'}"
        dev_href = z.Device.href if z.Device is not None else ""
        lines.append(
            f"| `{z.href}` | {z.Name or '?'} | {z.ControlType or '?'} | {cat} | `{dev_href}` |"
        )
    lines.append("")

    # Keypads — buttons + resolved actions
    lines.append("## Keypads — Buttons & Programming")
    lines.append("")
    lines.append("_For each keypad/pico/remote: every button with its engraving and what it does._")
    lines.append("")
    devices_by_href: dict[str, Device] = {d.href: d for d in inv.devices}

    if not inv.button_group_expansions:
        lines.append("_No keypad button data captured._")
        lines.append("")
    else:
        for dhref, bgs in sorted(inv.button_group_expansions.items()):
            d = devices_by_href.get(dhref)
            if d is None:
                continue
            ahref = d.AssociatedArea.href if d.AssociatedArea is not None else None
            lines.append(f"### {d.Name or '?'} — `{dhref}`")
            lines.append(
                f"_{d.DeviceType} {d.ModelNumber or ''} · "
                f"Area: {area_path(ahref, areas_by_href) if ahref else '?'} · "
                f"SN: {d.SerialNumber or '?'}_"
            )
            lines.append("")
            lines.append("| # | Engraving / Name | ButtonType | Action |")
            lines.append("|---:|---|---|---|")
            for bg in bgs:
                for btn in bg.Buttons or []:
                    eng_text = btn.Engraving.Text if btn.Engraving is not None else None
                    action = resolve_button_action(
                        btn, inv.programming_models, inv.presets, zones_by_href
                    )
                    lines.append(
                        f"| {btn.ButtonNumber or '?'} | "
                        f"{eng_text or btn.Name or ''} | "
                        f"`{btn.ButtonType or '?'}` | "
                        f"{action} |"
                    )
            lines.append("")

    # Virtual buttons
    if inv.virtual_buttons:
        lines.append("## Virtual Buttons (timeclock / scene targets)")
        lines.append("")
        lines.append("| href | Name | Category | ProgrammingModel |")
        lines.append("|---|---|---|---|")
        for v in sorted(inv.virtual_buttons, key=lambda v: v.href):
            cat = ""
            if v.Category is not None and isinstance(v.Category, dict):
                cat = v.Category.get("Type", "?")
            pm_href = v.ProgrammingModel.href if v.ProgrammingModel is not None else ""
            lines.append(f"| `{v.href}` | {v.Name or '?'} | {cat} | `{pm_href}` |")
        lines.append("")

    # Area scenes
    if inv.area_scenes:
        lines.append("## Area Scenes")
        lines.append("")
        lines.append("| href | Name | Area | ProgrammingModel |")
        lines.append("|---|---|---|---|")
        for s in sorted(inv.area_scenes, key=lambda s: s.href):
            phref = s.Parent.href if s.Parent is not None else None
            pm_href = s.ProgrammingModel.href if s.ProgrammingModel is not None else ""
            area_label = area_path(phref, areas_by_href) if phref else "?"
            lines.append(f"| `{s.href}` | {s.Name or '?'} | {area_label} | `{pm_href}` |")
        lines.append("")

    # Timeclock
    if inv.timeclock_event_rules:
        lines.append("## Timeclock Event Rules")
        lines.append("")
        lines.append("| href | Name | Enabled | Days | TimeReference |")
        lines.append("|---|---|---|---|---|")
        for t in inv.timeclock_event_rules:
            days = t.DaysOfWeek if t.DaysOfWeek else "?"
            tref = t.TimeReference
            tref_str = tref.EventName if hasattr(tref, "EventName") and tref.EventName else str(tref or "?")  # type: ignore[union-attr]
            lines.append(
                f"| `{t.href}` | {t.Name or '?'} | {t.Enabled} | {days} | {tref_str} |"
            )
        lines.append("")

    return "\n".join(lines) + "\n"
