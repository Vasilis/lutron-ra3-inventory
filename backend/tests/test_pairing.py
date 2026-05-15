"""Pairing route regressions around credential-storage policy."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ra3_inventory.api.dto import PairStartRequest
from ra3_inventory.api.events import EventBus, sse_stream
from ra3_inventory.api.routes.pairing import _run_pairing
from ra3_inventory.config import Config
from ra3_inventory.storage.certs import has_encrypted_pairing, has_plain_pairing


@pytest.mark.asyncio
async def test_pairing_requires_passphrase_when_keychain_unavailable(monkeypatch) -> None:
    monkeypatch.setattr("ra3_inventory.api.routes.pairing.keychain.is_available", lambda: False)
    bus = EventBus()
    channel = await bus.create("pair")
    app = SimpleNamespace(state=SimpleNamespace(event_bus=bus, config=Config()))

    await _run_pairing(app, channel.id, PairStartRequest(host="192.0.2.1"))

    retained = await bus.get(channel.id)
    assert retained is not None
    event = await anext(sse_stream(retained))
    assert event["event"] == "error"
    assert "disk_passphrase" in event["data"]

    await bus.drop(channel.id)


@pytest.mark.asyncio
async def test_pairing_uses_encrypted_disk_fallback_when_passphrase_is_supplied(
    monkeypatch, tmp_path
) -> None:
    class FakeProto:
        async def run(self) -> None:
            return None

        async def request(self, communique_type: str, url: str):
            return SimpleNamespace(
                Body={
                    "Devices": [
                        {
                            "href": "/device/1",
                            "DeviceType": "RadioRa3Processor",
                            "SerialNumber": "abc",
                        }
                    ]
                }
            )

        def close(self) -> None:
            return None

        async def wait_closed(self) -> None:
            return None

    async def fake_pair(host: str, ready):
        ready()
        return {"key": "KEY", "cert": "CERT", "ca": "CA", "version": "1"}

    async def fake_connect(host: str, **kwargs):
        return FakeProto()

    monkeypatch.setattr("ra3_inventory.storage.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("ra3_inventory.api.routes.pairing.keychain.is_available", lambda: False)
    monkeypatch.setattr("ra3_inventory.api.routes.pairing.async_pair", fake_pair)
    monkeypatch.setattr("ra3_inventory.api.routes.pairing.connect_leap", fake_connect)

    bus = EventBus()
    channel = await bus.create("pair")
    cfg = Config()
    app = SimpleNamespace(state=SimpleNamespace(event_bus=bus, config=cfg))

    await _run_pairing(
        app,
        channel.id,
        PairStartRequest(host="192.0.2.1", disk_passphrase="secret"),
    )

    assert cfg.active_profile_serial == "abc"
    assert has_encrypted_pairing("abc")
    assert not has_plain_pairing("abc")

    await bus.drop(channel.id)
