"""Resolve a Button → ProgrammingModel → Preset → Assignment chain into a human-readable action.

This is the logic that produces "press:dim(Kitchen Island)=80" style strings
in the Markdown report. Ported from ``resolve_button_action()`` in
``docs/legacy/lutron_raw_extract.py``, adapted to operate on typed Pydantic
models instead of raw dicts.
"""

from __future__ import annotations

from ..models import Assignment, Button, Preset, ProgrammingModel, Zone

ACTION_KEYS: tuple[tuple[str, str], ...] = (
    ("PressOnPresetAssignments", "press"),
    ("ReleaseOnPresetAssignments", "release"),
    ("DoubleTapOnPresetAssignments", "double-tap"),
    ("HoldOnPresetAssignments", "hold"),
)

ASN_KEYS: tuple[tuple[str, str, str], ...] = (
    ("DimmedLevelAssignments", "dim", "Level"),
    ("FanSpeedAssignments", "fan", "FanSpeed"),
    ("TiltAssignments", "tilt", "Tilt"),
    ("SwitchedLevelAssignments", "switch", "SwitchedLevel"),
)


def _zone_label(href: str | None, zones: dict[str, Zone]) -> str:
    if not href:
        return "?"
    z = zones.get(href)
    if z is None:
        return href
    return z.Name or href


def _level_field(assignment: Assignment, field: str) -> object:
    """Read the requested level/speed/tilt field; fall back to ``Level``."""
    val = getattr(assignment, field, None)
    if val is None:
        val = assignment.Level
    return val


def resolve_button_action(
    btn: Button,
    programming_models: dict[str, ProgrammingModel],
    presets: dict[str, Preset],
    zones: dict[str, Zone],
) -> str:
    """Return a human-readable summary of what a button does.

    Examples:
        ``SimpleConditional · press:dim(Kitchen Island)=80``
        ``MultiTap · press:switch(Hallway)=On · double-tap:switch(Hallway)=Off``
    """
    pm_ref = btn.ProgrammingModel
    if pm_ref is None or not pm_ref.href:
        return "(no PM)"
    pm = programming_models.get(pm_ref.href)
    if pm is None:
        return f"(PM {pm_ref.href} not pulled)"

    bits: list[str] = []
    for action_attr, action_label in ACTION_KEYS:
        action_refs = getattr(pm, action_attr, None) or []
        for ref in action_refs:
            preset = presets.get(ref.href)
            if preset is None:
                continue
            for asn_attr, asn_label, level_field in ASN_KEYS:
                assignments = getattr(preset, asn_attr, None) or []
                for asn in assignments:
                    zhref = asn.AssignableObject.href if asn.AssignableObject is not None else None
                    zname = _zone_label(zhref, zones)
                    level = _level_field(asn, level_field)
                    bits.append(f"{action_label}:{asn_label}({zname})={level}")

    pm_type = pm.ProgrammingModelType or "?"
    if not bits:
        return f"{pm_type} (no assignments)"
    return f"{pm_type} · " + " · ".join(bits)
