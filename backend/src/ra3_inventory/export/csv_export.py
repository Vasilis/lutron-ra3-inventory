"""CSV export — one CSV per category, bundled in a zip."""

from __future__ import annotations

import csv
import io
import zipfile

from ..models import ProcessorInventory, area_path
from ._resolver import resolve_button_action


def _csv(rows: list[dict], fieldnames: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def to_csv_zip(inv: ProcessorInventory) -> bytes:
    """Return a ZIP containing devices.csv, zones.csv, buttons.csv, areas.csv."""
    areas_by_href = {a.href: a for a in inv.areas}
    zones_by_href = {z.href: z for z in inv.zones}
    devices_by_href = {d.href: d for d in inv.devices}

    # Devices
    device_rows = []
    for d in inv.devices:
        ahref = d.AssociatedArea.href if d.AssociatedArea else None
        device_rows.append(
            {
                "href": d.href,
                "Name": d.Name or "",
                "DeviceType": d.DeviceType,
                "ModelNumber": d.ModelNumber or "",
                "SerialNumber": d.SerialNumber or "",
                "Firmware": d.firmware_display_name or "",
                "AddressedState": d.AddressedState or "",
                "Area": area_path(ahref, areas_by_href) if ahref else "",
            }
        )
    device_csv = _csv(
        device_rows,
        [
            "href",
            "Name",
            "DeviceType",
            "ModelNumber",
            "SerialNumber",
            "Firmware",
            "AddressedState",
            "Area",
        ],
    )

    # Zones
    zone_rows = []
    for z in inv.zones:
        cat = ""
        if z.Category:
            cat = f"{z.Category.Type or ''}/{z.Category.SubType or ''}"
        zone_rows.append(
            {
                "href": z.href,
                "Name": z.Name or "",
                "ControlType": z.ControlType or "",
                "Category": cat,
                "Device": z.Device.href if z.Device else "",
            }
        )
    zone_csv = _csv(zone_rows, ["href", "Name", "ControlType", "Category", "Device"])

    # Areas
    area_rows = []
    for a in inv.areas:
        area_rows.append(
            {
                "href": a.href,
                "Name": a.Name or "",
                "Parent": a.Parent.href if a.Parent else "",
                "FullPath": area_path(a.href, areas_by_href),
            }
        )
    area_csv = _csv(area_rows, ["href", "Name", "Parent", "FullPath"])

    # Buttons (with resolved action)
    button_rows = []
    for dhref, bgs in inv.button_group_expansions.items():
        d = devices_by_href.get(dhref)
        device_name = d.Name if d else ""
        for bg in bgs:
            for btn in bg.Buttons or []:
                action = resolve_button_action(
                    btn, inv.programming_models, inv.presets, zones_by_href
                )
                eng = btn.Engraving.Text if btn.Engraving else ""
                button_rows.append(
                    {
                        "device_href": dhref,
                        "device_name": device_name,
                        "button_href": btn.href,
                        "ButtonNumber": btn.ButtonNumber or "",
                        "Engraving": eng or "",
                        "Name": btn.Name or "",
                        "ButtonType": btn.ButtonType or "",
                        "Action": action,
                    }
                )
    button_csv = _csv(
        button_rows,
        [
            "device_href",
            "device_name",
            "button_href",
            "ButtonNumber",
            "Engraving",
            "Name",
            "ButtonType",
            "Action",
        ],
    )

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("devices.csv", device_csv)
        zf.writestr("zones.csv", zone_csv)
        zf.writestr("areas.csv", area_csv)
        zf.writestr("buttons.csv", button_csv)
    return out.getvalue()
