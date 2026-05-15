"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RA3_DIR = FIXTURES_DIR / "ra3"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to ``backend/tests/fixtures/``."""
    return FIXTURES_DIR


@pytest.fixture
def ra3_dir() -> Path:
    """Path to the RA3 fixture set (real LEAP responses from a known RA3)."""
    return RA3_DIR


@pytest.fixture
def ra3_processor_body() -> dict:
    """The Body block from ``/device?where=IsThisDevice:true`` on the test RA3."""
    return json.loads((RA3_DIR / "processor.json").read_text())["Body"]


@pytest.fixture
def ra3_devices_body() -> dict:
    """The Body block from ``/device?where=IsThisDevice:false``."""
    return json.loads((RA3_DIR / "device-list.json").read_text())["Body"]


@pytest.fixture
def ra3_areas_body() -> dict:
    return json.loads((RA3_DIR / "areas.json").read_text())["Body"]


@pytest.fixture
def ra3_project_body() -> dict:
    return json.loads((RA3_DIR / "project.json").read_text())["Body"]
