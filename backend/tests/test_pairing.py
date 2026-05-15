"""Pairing route regressions around credential-storage policy."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ra3_inventory.api.dto import PairStartRequest
from ra3_inventory.api.events import EventBus, sse_stream
from ra3_inventory.api.routes.pairing import _run_pairing
from ra3_inventory.config import Config


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
