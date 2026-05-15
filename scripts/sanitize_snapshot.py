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

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "src"))

from ra3_inventory.sanitize import sanitize_snapshot_data  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Sanitize a ProcessorInventory snapshot.")
    p.add_argument("input", help="snapshot JSON file")
    p.add_argument("output", help="output path (will be created)")
    args = p.parse_args()

    inp = Path(args.input).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    data = json.loads(inp.read_text())
    data = sanitize_snapshot_data(data)
    out.write_text(json.dumps(data, indent=2, default=str))
    print(f"Wrote sanitized snapshot: {out}")

    # Quick round-trip test
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
