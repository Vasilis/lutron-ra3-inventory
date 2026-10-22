"""Default paths and explicit credential mocks must remain test-local."""

from pathlib import Path

import keyring
from keyring.backends.null import Keyring as NullKeyring

from ra3_inventory.config import Config
from ra3_inventory.storage import keychain
from ra3_inventory.storage.paths import config_path, ensure_profile_tree, profile_dir


def test_default_config_and_profile_writes_stay_in_test_directory(tmp_path: Path) -> None:
    config = Config.load()
    assert config.active_profile_serial is None
    config.active_profile_serial = "synthetic-profile"
    config.save()
    ensure_profile_tree("synthetic-profile")

    assert config_path().is_relative_to(tmp_path)
    assert profile_dir("synthetic-profile").is_relative_to(tmp_path)
    assert Config.load().active_profile_serial == "synthetic-profile"


def test_explicit_mock_backend_still_overrides_isolated_default() -> None:
    class MockBackend(NullKeyring):
        def get_password(self, service: str, username: str) -> str | None:
            assert service == "com.ra3inventory.synthetic-profile"
            return {"key": "KEY", "cert": "CERT", "ca": "CA"}[username]

    assert keychain.load_pairing("synthetic-profile") is None
    keyring.set_keyring(MockBackend())
    assert keychain.load_pairing("synthetic-profile") == ("KEY", "CERT", "CA")
