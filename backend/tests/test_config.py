"""Config-load recovery behavior."""

from __future__ import annotations

from ra3_inventory.config import Config


def test_malformed_config_is_backed_up_and_recreated(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    path = tmp_path / "config.json"
    path.write_text("{not-json")

    cfg = Config.load()

    assert cfg.active_profile_serial is None
    assert (tmp_path / "config.json.corrupt").read_text() == "{not-json"
    assert path.exists()
