"""Markdown report export — typed re-implementation of the legacy script's report.

Ported from ``build_inventory_md()`` in ``docs/legacy/lutron_raw_extract.py``.
Operates on a typed ``ProcessorInventory`` instead of raw dicts, but produces
a Markdown structure intentionally close to the legacy output so the visual
diff for users moving from the standalone script is minimal.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ..models import (
    Area,
    Device,
    ProcessorInventory,
    Zone,
    area_path,
)
from ._resolver import resolve_button_action


def _firmware_display(d: Device) -> str:
    return d.firmware_display_name or "_(none)_"


def _href_id(href: str | None) -> str:
    return (href or "").rsplit("/", 1)[-1] or ""


def _format_timestamp(ts: object) -> str:
    """Format ``Project.ProjectModifiedTimestamp`` for human display.

    The processor returns this in two shapes:
      - a flat ISO8601-ish string (older firmware)
      - a ``{Year, Month, Day, Hour, Minute, Second, Utc}`` dict (26.x+)
    """
    if isinstance(ts, dict):
        try:
            y = int(ts.get("Year", 0))
            mo = int(ts.get("Month", 0))
            da = int(ts.get("Day", 0))
            h = int(ts.get("Hour", 0))
            mi = int(ts.get("Minute", 0))
            s = int(ts.get("Second", 0))
            return f"{y:04d}-{mo:02d}-{da:02d}T{h:02d}:{mi:02d}:{s:02d}Z"
        except (TypeError, ValueError):
            return str(ts)
    return str(ts)


def _count_buttons_in_expansions(inv) -> int:
    """Total buttons across all expanded button groups."""
    return sum(len(bg.Buttons or []) for bgs in inv.button_group_expansions.values() for bg in bgs)


SECTION_KEYS: tuple[str, ...] = (
    "header",
    "processor",
    "summary",
    "device_types",
    "areas",
    "devices",
    "zones",
    "keypads",
    "virtual_buttons",
    "area_scenes",
    "timeclock",
)
"""Stable section keys for the Markdown report.

These match the values the frontend's ExportDialog uses for its
``?sections=...`` query string and the order in which they're rendered
in the report.
"""


_POSITION_RE = re.compile(r"^Position\s+\d+$", re.IGNORECASE)


def _position_display_name(d: Device, areas_by_href: dict[str, "Area"]) -> str:
    """Substitute the parent area's name when ``Device.Name`` is ``Position N``.

    Mirrors the frontend's ``deviceDisplayName`` so live UI and exported
    reports use the same label.
    """
    raw = d.Name or d.DeviceType
    if not _POSITION_RE.match(raw):
        return raw
    if d.AssociatedArea is not None and d.AssociatedArea.href in areas_by_href:
        area_name = areas_by_href[d.AssociatedArea.href].Name
        if area_name:
            return area_name
    return raw


def to_markdown(
    inv: ProcessorInventory,
    sections: set[str] | None = None,
    *,
    verbose: bool = False,
) -> str:
    """Build a human-readable Markdown report for one ProcessorInventory.

    Args:
        sections: optional set of keys from :data:`SECTION_KEYS` to include.
            ``None`` (the default) means *all* sections. Unknown keys are
            ignored.
        verbose: when ``True`` emit the full RA3 LEAP detail (every column,
            href, AddressedState, full button action chain). When ``False``
            (the default) emit a recovery-focused subset — just enough that
            you could rebuild the project from scratch after a factory
            reset. Device tables drop href / AddressedState / LocalZones /
            ButtonGroups columns; zones drop href / Category; keypad
            sections collapse to per-button engravings rather than the full
            programming-model breakdown.
    """
    selected = set(SECTION_KEYS) if sections is None else (sections & set(SECTION_KEYS))

    areas_by_href: dict[str, Area] = {a.href: a for a in inv.areas}
    zones_by_href: dict[str, Zone] = {z.href: z for z in inv.zones}

    lines: list[str] = []

    if "header" in selected:
        lines.append(f"# Lutron Inventory — {inv.host}")
        lines.append("")
        lines.append(f"**Project:** {inv.project.Name or '?'}  ")
        lines.append(f"**ProductType:** `{inv.project.ProductType or '?'}`  ")
        if inv.project.ProjectModifiedTimestamp:
            lines.append(
                f"**Project Modified:** {_format_timestamp(inv.project.ProjectModifiedTimestamp)}  "
            )
        lines.append(f"**Extracted at:** {inv.extracted_at.isoformat()}  ")
        lines.append(f"**Schema:** v{inv.schema_version}")
        if inv.partial:
            lines.append("")
            lines.append(
                "> **Note:** this snapshot is marked `partial=true` — the processor's "
                "project was modified during extraction."
            )
        lines.append("")

    if "processor" not in selected:
        return _emit_remaining_sections(
            lines, inv, areas_by_href, zones_by_href, selected, verbose
        )

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
    if verbose:
        lines.append(f"| href | `{p.href}` |")
    lines.append(f"| Name | {p.Name or '?'} |")
    lines.append(f"| DeviceType | `{p.DeviceType}` |")
    lines.append(f"| ModelNumber | {p.ModelNumber or '?'} |")
    lines.append(f"| SerialNumber | {p.SerialNumber or '?'} |")
    lines.append(f"| Firmware | {_firmware_display(p)} |")
    lines.append(f"| MAC | {mac or '?'} |")
    if verbose:
        lines.append(f"| AddressedState | {p.AddressedState or '?'} |")
    lines.append("")

    return _emit_remaining_sections(
        lines, inv, areas_by_href, zones_by_href, selected, verbose
    )


def _emit_remaining_sections(
    lines: list[str],
    inv: ProcessorInventory,
    areas_by_href: dict[str, "Area"],
    zones_by_href: dict[str, "Zone"],
    selected: set[str],
    verbose: bool,
) -> str:
    """Emit every section after Processor. Split out so the Processor block
    can short-circuit if it's deselected."""

    if "summary" in selected:
        lines.append("## Summary")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|---|---:|")
        lines.append(f"| Areas | {len(inv.areas)} |")
        lines.append(f"| Devices (excl. processor) | {len(inv.devices)} |")
        lines.append(f"| Zones | {len(inv.zones)} |")
        # On newer RA3 firmware the bulk /button endpoint isn't supported; the
        # real button count lives inside button_group_expansions.
        button_count = len(inv.buttons) or _count_buttons_in_expansions(inv)
        lines.append(f"| Buttons | {button_count} |")
        lines.append(f"| LEDs | {len(inv.leds)} |")
        lines.append(f"| Virtual buttons | {len(inv.virtual_buttons)} |")
        lines.append(f"| Area scenes | {len(inv.area_scenes)} |")
        lines.append(f"| ProgrammingModels resolved | {len(inv.programming_models)} |")
        lines.append(f"| Presets resolved | {len(inv.presets)} |")
        lines.append("")

    if "device_types" in selected:
        type_counts: dict[tuple[str, str], int] = defaultdict(int)
        for d in inv.devices:
            type_counts[(d.DeviceType, d.ModelNumber or "_(none)_")] += 1
        lines.append("## Device Type x Model")
        lines.append("")
        lines.append("| Count | DeviceType | ModelNumber |")
        lines.append("|---:|---|---|")
        for (t, m), n in sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| {n} | `{t}` | {m} |")
        lines.append("")

    if "areas" in selected:
        lines.append("## Areas")
        lines.append("")
        sorted_areas = sorted(inv.areas, key=lambda a: area_path(a.href, areas_by_href))
        if verbose:
            lines.append("| href | Name | Parent | Full path |")
            lines.append("|---|---|---|---|")
            for a in sorted_areas:
                phref = a.Parent.href if a.Parent is not None else None
                lines.append(
                    f"| `{a.href}` | {a.Name or '?'} | `{phref or 'root'}` | "
                    f"{area_path(a.href, areas_by_href)} |"
                )
        else:
            lines.append("| Area | Full path |")
            lines.append("|---|---|")
            for a in sorted_areas:
                lines.append(
                    f"| {a.Name or '?'} | {area_path(a.href, areas_by_href)} |"
                )
        lines.append("")

    if "devices" in selected:
        by_area: dict[str | None, list[Device]] = defaultdict(list)
        for d in inv.devices:
            ahref = d.AssociatedArea.href if d.AssociatedArea is not None else None
            by_area[ahref].append(d)

        lines.append("## Devices by Area" + (" (full fields)" if verbose else ""))
        lines.append("")
        for ahref in sorted(by_area.keys(), key=lambda h: area_path(h, areas_by_href) if h else "zzz"):
            label = area_path(ahref, areas_by_href) if ahref else "_(unassigned)_"
            lines.append(f"### {label}")
            lines.append("")
            if verbose:
                lines.append(
                    "| href | Name | DeviceType | ModelNumber | SerialNumber | "
                    "Firmware | Addressed | LocalZones | ButtonGroups |"
                )
                lines.append("|---|---|---|---|---|---|---|---|---|")
                for d in sorted(by_area[ahref], key=lambda x: (x.DeviceType, x.Name or "")):
                    lz = ", ".join(_href_id(r.href) for r in d.LocalZones) or "_(none)_"
                    bg = ", ".join(_href_id(r.href) for r in d.ButtonGroups) or "_(none)_"
                    lines.append(
                        f"| `{d.href}` | {d.Name or '?'} | `{d.DeviceType}` | "
                        f"{d.ModelNumber or '_(none)_'} | {d.SerialNumber or '_(none)_'} | "
                        f"{_firmware_display(d)} | {d.AddressedState or '?'} | {lz} | {bg} |"
                    )
            else:
                # Recovery-essentials: just the columns you'd need to
                # re-address every device after a factory reset.
                lines.append("| Name | Type | Model | Serial | Firmware |")
                lines.append("|---|---|---|---|---|")
                for d in sorted(by_area[ahref], key=lambda x: (x.DeviceType, x.Name or "")):
                    name = _position_display_name(d, areas_by_href)
                    if d.Name and _POSITION_RE.match(d.Name) and d.Name != name:
                        name = f"{name} ({d.Name})"
                    lines.append(
                        f"| {name} | {d.DeviceType} | "
                        f"{d.ModelNumber or '_(none)_'} | "
                        f"{d.SerialNumber if d.SerialNumber is not None else '_(none)_'} | "
                        f"{_firmware_display(d)} |"
                    )
            lines.append("")

    if "zones" in selected:
        lines.append("## Zones")
        lines.append("")
        devices_by_href: dict[str, Device] = {d.href: d for d in inv.devices}
        if verbose:
            lines.append("| href | Name | ControlType | Category | Device |")
            lines.append("|---|---|---|---|---|")
            for z in sorted(inv.zones, key=lambda z: z.Name or ""):
                cat = ""
                if z.Category is not None:
                    cat = f"{z.Category.Type or '?'}/{z.Category.SubType or '?'}"
                dev_href = z.Device.href if z.Device is not None else ""
                lines.append(
                    f"| `{z.href}` | {z.Name or '?'} | {z.ControlType or '?'} | "
                    f"{cat} | `{dev_href}` |"
                )
        else:
            lines.append("| Zone | Control type | Controlling device |")
            lines.append("|---|---|---|")
            for z in sorted(inv.zones, key=lambda z: z.Name or ""):
                ctrl = z.ControlType or "?"
                dev_label = ""
                if z.Device is not None and z.Device.href in devices_by_href:
                    dev_label = _position_display_name(
                        devices_by_href[z.Device.href], areas_by_href
                    )
                lines.append(f"| {z.Name or '?'} | {ctrl} | {dev_label or '?'} |")
        lines.append("")

    if "keypads" in selected:
        if verbose:
            lines.append("## Keypads — Buttons & Programming")
            lines.append("")
            lines.append(
                "_For each keypad/pico/remote: every button with its engraving "
                "and what it does._"
            )
        else:
            lines.append("## Keypads — Button Engravings")
            lines.append("")
            lines.append(
                "_The button labels you'll need to recreate after a factory "
                "reset. Re-program each button's actions in Lutron Designer._"
            )
        lines.append("")
        devices_by_href2: dict[str, Device] = {d.href: d for d in inv.devices}

        if not inv.button_group_expansions:
            lines.append("_No keypad button data captured._")
            lines.append("")
        elif verbose:
            for dhref, bgs in sorted(inv.button_group_expansions.items()):
                d = devices_by_href2.get(dhref)
                if d is None:
                    continue
                ahref = d.AssociatedArea.href if d.AssociatedArea is not None else None
                lines.append(f"### {_position_display_name(d, areas_by_href)} — `{dhref}`")
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
        else:
            # Recovery-essentials: one row per keypad with comma-separated
            # button labels. No href, no per-button table, no PM action chain
            # (which on RA3 26.x isn't reachable over LEAP anyway).
            lines.append("| Keypad | Area | Model | Button engravings |")
            lines.append("|---|---|---|---|")
            for dhref, bgs in sorted(inv.button_group_expansions.items()):
                d = devices_by_href2.get(dhref)
                if d is None:
                    continue
                labels: list[str] = []
                for bg in bgs:
                    for btn in bg.Buttons or []:
                        eng_text = btn.Engraving.Text if btn.Engraving is not None else None
                        label = eng_text or btn.Name or "?"
                        # Engravings can contain newlines (multi-line wall
                        # plate labels). Inline them in the recovery table
                        # so the row stays on one line.
                        label = " ".join(label.split())
                        labels.append(f"{btn.ButtonNumber or '?'}={label}")
                ahref = d.AssociatedArea.href if d.AssociatedArea is not None else None
                area_label = area_path(ahref, areas_by_href) if ahref else "?"
                lines.append(
                    f"| {_position_display_name(d, areas_by_href)} | "
                    f"{area_label} | {d.ModelNumber or '_(none)_'} | "
                    f"{', '.join(labels) if labels else '_(none)_'} |"
                )
            lines.append("")

    if "virtual_buttons" in selected and inv.virtual_buttons:
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

    if "area_scenes" in selected and inv.area_scenes:
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

    if "timeclock" in selected and inv.timeclock_event_rules:
        lines.append("## Timeclock Event Rules")
        lines.append("")
        lines.append("| href | Name | Enabled | Days | TimeReference |")
        lines.append("|---|---|---|---|---|")
        for t in inv.timeclock_event_rules:
            days = t.DaysOfWeek if t.DaysOfWeek else "?"
            tref = t.TimeReference
            tref_str = (
                tref.EventName
                if hasattr(tref, "EventName") and tref.EventName
                else str(tref or "?")
            )  # type: ignore[union-attr]
            lines.append(f"| `{t.href}` | {t.Name or '?'} | {t.Enabled} | {days} | {tref_str} |")
        lines.append("")

    return "\n".join(lines) + "\n"
