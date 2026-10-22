"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import keyring.core
import pytest
from keyring.backends.null import Keyring as NullKeyring

from ra3_inventory import config as app_config
from ra3_inventory.storage import paths

# Install before test-module collection, not only before test bodies. App paths
# are computed on demand; config also imports app_data_dir directly. No current
# production module reads profile paths or probes Keychain at import time.
_collection_state = TemporaryDirectory(prefix="ra3-pytest-collection-")
_collection_patch = pytest.MonkeyPatch()
_collection_root = Path(_collection_state.name)
_collection_patch.setattr(paths, "app_data_dir", lambda: _collection_root)
_collection_patch.setattr(app_config, "app_data_dir", lambda: _collection_root)
# Do not call get_keyring(): that would discover/probe a real host backend before
# isolation. Patching its lazy cache is test-only and permits explicit mocks.
_collection_patch.setattr(keyring.core, "_keyring_backend", NullKeyring())


def pytest_unconfigure(config: pytest.Config) -> None:
    """Restore process-local defaults after all fixture/test teardown."""
    _collection_patch.undo()
    _collection_state.cleanup()


@pytest.fixture(autouse=True)
def isolated_app_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Every test starts with empty app state and no real credential backend."""
    root = tmp_path / "app-data"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(paths, "app_data_dir", lambda: root)
    monkeypatch.setattr(app_config, "app_data_dir", lambda: root)
    monkeypatch.setattr(keyring.core, "_keyring_backend", NullKeyring())


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
