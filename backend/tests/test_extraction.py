"""Extraction-route regressions."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ra3_inventory.api.dto import ExtractStartRequest
from ra3_inventory.api.events import EventBus, sse_stream
from ra3_inventory.api.routes.extraction import _run_extraction


@pytest.mark.asyncio
async def test_extraction_reports_missing_credentials_as_typed_error(monkeypatch) -> None:
    monkeypatch.setattr(
        "ra3_inventory.api.routes.extraction.materialize_pairing",
        lambda serial, passphrase=None: None,
    )
    bus = EventBus()
    channel = await bus.create("extract")
    app = SimpleNamespace(state=SimpleNamespace(event_bus=bus))

    await _run_extraction(app, channel.id, ExtractStartRequest(profile_serial="abc"))

    retained = await bus.get(channel.id)
    assert retained is not None
    event = await anext(sse_stream(retained))
    assert event["event"] == "error"
    assert '"kind": "missing_credentials"' in event["data"]
    await bus.drop(channel.id)
