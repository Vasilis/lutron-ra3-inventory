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


def _preset_actions_for_pm(pm: ProgrammingModel) -> list[tuple[str, str]]:
    """Return ``[(action_label, preset_href), ...]`` for a given PM.

    Handles both the legacy ``*OnPresetAssignments[]`` schema described in the
    user's brief and the newer RA 3 firmware schemas (26.03+):

    - ``AdvancedToggleProgrammingModel``: ``AdvancedToggleProperties.{Primary,
      Secondary}Preset.href`` — primary state vs. secondary state of a toggle.
    - ``SingleActionProgrammingModel``: ``Preset.href`` — a one-shot press.
    - ``SingleSceneRaiseProgrammingModel`` / ``SingleSceneLowerProgrammingModel``:
      ``Preset.href`` plus a ``Direction`` field — continuous raise/lower.
    """
    out: list[tuple[str, str]] = []

    # Legacy schema
    for action_attr, action_label in ACTION_KEYS:
        action_refs = getattr(pm, action_attr, None) or []
        for ref in action_refs:
            if ref.href:
                out.append((action_label, ref.href))

    # Newer schemas live in ``model_extra`` (RA3Resource is extra="allow").
    extra = pm.model_extra or {}
    advanced = extra.get("AdvancedToggleProperties")
    if isinstance(advanced, dict):
        for state_label, key in (("toggle-primary", "PrimaryPreset"),
                                 ("toggle-secondary", "SecondaryPreset")):
            block = advanced.get(key)
            if isinstance(block, dict) and isinstance(block.get("href"), str):
                out.append((state_label, block["href"]))

    single_preset = extra.get("Preset")
    if isinstance(single_preset, dict) and isinstance(single_preset.get("href"), str):
        pm_type = pm.ProgrammingModelType or ""
        if "Raise" in pm_type:
            label = "raise"
        elif "Lower" in pm_type:
            label = "lower"
        else:
            label = "press"
        out.append((label, single_preset["href"]))

    return out


def resolve_button_action(
    btn: Button,
    programming_models: dict[str, ProgrammingModel],
    presets: dict[str, Preset],
    zones: dict[str, Zone],
) -> str:
    """Return a human-readable summary of what a button does.

    Examples:
        ``SimpleConditional · press:dim(Kitchen Island)=80``
        ``AdvancedToggleProgrammingModel · toggle-primary:dim(Living)=80 · toggle-secondary:dim(Living)=0``
    """
    pm_ref = btn.ProgrammingModel
    if pm_ref is None or not pm_ref.href:
        return "(no PM)"
    pm = programming_models.get(pm_ref.href)
    if pm is None:
        return f"(PM {pm_ref.href} not pulled)"

    bits: list[str] = []
    for action_label, preset_href in _preset_actions_for_pm(pm):
        preset = presets.get(preset_href)
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
