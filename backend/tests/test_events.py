"""Regression tests for SSE channel retention."""

from __future__ import annotations

import pytest

from ra3_inventory.api.events import EventBus, sse_stream


@pytest.mark.asyncio
async def test_finished_channel_remains_available_for_late_subscriber() -> None:
    bus = EventBus()
    channel = await bus.create("extract")
    await channel.publish({"phase": "success", "detail": "done"})

    await bus.finish(channel.id, retention_seconds=0.05)

    late_channel = await bus.get(channel.id)
    assert late_channel is channel
    event = await anext(sse_stream(late_channel))
    assert event["event"] == "success"

    await bus.drop(channel.id)
