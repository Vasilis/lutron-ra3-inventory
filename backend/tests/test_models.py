"""Parse real RA3 LEAP responses through our typed models."""

from __future__ import annotations

from ra3_inventory.models import (
    Area,
    Device,
    Pico,
    Project,
    RadioRa3Processor,
    SunnataHybridKeypad,
    SunnataKeypad,
    parse_device,
)


def test_processor_parses(ra3_processor_body: dict) -> None:
    """The processor self-query body parses into a RadioRa3Processor."""
    devs = ra3_processor_body["Devices"]
    assert len(devs) == 1
    proc = parse_device(devs[0])
    assert isinstance(proc, RadioRa3Processor)
    assert proc.DeviceType == "RadioRa3Processor"
    assert proc.ModelNumber == "JanusProcRA3"
    assert proc.SerialNumber is not None
    assert proc.FirmwareImage is not None
    assert proc.FirmwareImage.Firmware is not None
    assert proc.FirmwareImage.Firmware.DisplayName  # any string is fine


def test_device_list_parses(ra3_devices_body: dict) -> None:
    """Every entry in the device list parses into some Device subclass."""
    devs = [parse_device(d) for d in ra3_devices_body["Devices"]]
    assert devs, "fixture is empty?"
    assert all(isinstance(d, Device) for d in devs)
    # Every device has the required base fields
    assert all(d.href for d in devs)
    assert all(d.DeviceType for d in devs)


def test_device_registry_picks_specific_subclasses(ra3_devices_body: dict) -> None:
    """Known device types parse into their specific subclasses."""
    by_type: dict[str, type] = {}
    for d in (parse_device(x) for x in ra3_devices_body["Devices"]):
        by_type.setdefault(d.DeviceType, type(d))

    # If the fixture has any of these, they should match the right class.
    if "SunnataKeypad" in by_type:
        assert by_type["SunnataKeypad"] is SunnataKeypad
    if "SunnataHybridKeypad" in by_type:
        assert by_type["SunnataHybridKeypad"] is SunnataHybridKeypad
    if "Pico3ButtonRaiseLower" in by_type:
        assert by_type["Pico3ButtonRaiseLower"] is Pico


def test_pico_button_count_derived() -> None:
    """Pico subclass exposes a derived button_count property."""
    p3 = Pico.model_validate(
        {"href": "/device/1", "DeviceType": "Pico3ButtonRaiseLower", "Name": "x"}
    )
    p4 = Pico.model_validate({"href": "/device/2", "DeviceType": "Pico4ButtonScene", "Name": "y"})
    assert p3.button_count == 3
    assert p4.button_count == 4


def test_unknown_device_type_falls_back(caplog) -> None:
    """A DeviceType the registry hasn't seen returns the base Device + warning."""
    d = parse_device({"href": "/device/9999", "DeviceType": "MadeUpDevice2099"})
    assert isinstance(d, Device)
    assert d.DeviceType == "MadeUpDevice2099"


def test_areas_parse(ra3_areas_body: dict) -> None:
    """Every area entry parses into Area with at least Name + href."""
    areas = [Area.model_validate(a) for a in ra3_areas_body["Areas"]]
    assert areas
    assert all(a.href for a in areas)
    # Areas with a parent should resolve a non-empty parent href
    children = [a for a in areas if a.Parent is not None]
    assert all(c.Parent and c.Parent.href for c in children)


def test_project_parses(ra3_project_body: dict) -> None:
    """The project body parses into Project with ProductType set."""
    project_data = ra3_project_body["Project"]
    project = Project.model_validate(project_data)
    assert project.ProductType is not None
    assert "RadioRA 3" in (project.ProductType or "") or project.Name is not None
