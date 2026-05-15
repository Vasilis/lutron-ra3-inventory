"""Round-trip the sanitized live fixture through the full pipeline.

This is the realest test we have: it loads ``examples/sanitized-snapshot.json``
(a redacted dump from the maintainer's own RA 3) and runs it through every
export, ensuring the typed pipeline is internally consistent.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from openpyxl import load_workbook

from ra3_inventory.export import to_csv_zip, to_json, to_markdown, to_xlsx
from ra3_inventory.models import ProcessorInventory

FIXTURE_PATH = Path(__file__).parent.parent.parent / "examples" / "sanitized-snapshot.json"


@pytest.fixture
def live_inventory() -> ProcessorInventory:
    if not FIXTURE_PATH.exists():
        pytest.skip(f"sanitized-snapshot.json not yet generated at {FIXTURE_PATH}")
    return ProcessorInventory.model_validate_json(FIXTURE_PATH.read_text())


def test_fixture_loads(live_inventory: ProcessorInventory) -> None:
    """The sanitized snapshot deserializes into our schema."""
    assert live_inventory.schema_version == 1
    assert live_inventory.areas, "no areas in fixture?"
    assert live_inventory.devices, "no devices in fixture?"
    assert live_inventory.zones, "no zones in fixture?"


def test_fixture_round_trips_json(live_inventory: ProcessorInventory) -> None:
    body = to_json(live_inventory)
    restored = ProcessorInventory.model_validate_json(body)
    assert len(restored.devices) == len(live_inventory.devices)
    assert len(restored.zones) == len(live_inventory.zones)


def test_fixture_markdown_has_real_structure(live_inventory: ProcessorInventory) -> None:
    md = to_markdown(live_inventory)
    assert md.startswith("# Lutron Inventory")
    assert "## Processor" in md
    assert "## Summary" in md
    assert "## Areas" in md
    assert "## Zones" in md
    assert "## Keypads — Buttons & Programming" in md

    # The buttons-from-expansions count should be > 0 even though the bulk
    # /button endpoint is empty on newer firmware.
    button_lines = [line for line in md.splitlines() if line.startswith("| Buttons |")]
    assert button_lines, "summary missing Buttons row"
    button_count = int(button_lines[0].split("|")[2].strip())
    assert button_count > 0, "expected non-zero button count from button_group_expansions"


def test_fixture_csv_has_buttons(live_inventory: ProcessorInventory) -> None:
    blob = to_csv_zip(live_inventory)
    z = zipfile.ZipFile(io.BytesIO(blob))
    button_csv = z.read("buttons.csv").decode("utf-8")
    # First non-header line should exist
    assert len(button_csv.splitlines()) > 1


def test_fixture_xlsx_loads(live_inventory: ProcessorInventory) -> None:
    blob = to_xlsx(live_inventory)
    wb = load_workbook(io.BytesIO(blob))
    assert {"Summary", "Devices", "Zones", "Areas", "Buttons"}.issubset(set(wb.sheetnames))
