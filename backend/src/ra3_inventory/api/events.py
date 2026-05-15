"""Server-Sent Events helpers — task-keyed event queues for pairing + extraction.

The pairing and extraction routes are long-running. The pattern:

1. POST ``/pair/start`` (or ``/extract``) creates an asyncio.Task that publishes
   events into an in-memory queue keyed by a fresh UUID, and returns that ID.
2. The client opens an EventSource on ``/pair/events?pair_id=<id>`` (or the
   matching ``/extract/events``), which streams from the queue until a
   terminal event (``success`` / ``error`` / ``done`` / ``timeout``).
3. The queue is reaped after the terminal event is delivered.

In-memory state is fine — this is a single-user, single-process app and
each LEAP operation is scoped to one webview session.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator, Coroutine
from dataclasses import dataclass, field
from typing import Any

_LOG = logging.getLogger(__name__)

TERMINAL_PHASES = {"done", "error", "timeout", "success"}


@dataclass
class EventChannel:
    """A queue of events for one in-flight task."""

    id: str
    queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)
    closed: bool = False

    async def publish(self, event: dict[str, Any]) -> None:
        if self.closed:
            return
        await self.queue.put(event)

    async def close(self) -> None:
        self.closed = True
        # Sentinel so any in-flight stream reader unblocks.
        await self.queue.put({"_close": True})


class EventBus:
    """Holds named event channels for the lifetime of the app."""

    def __init__(self) -> None:
        self._channels: dict[str, EventChannel] = {}
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[Any]] = set()

    async def create(self, prefix: str = "task") -> EventChannel:
        async with self._lock:
            cid = f"{prefix}-{uuid.uuid4().hex[:12]}"
            channel = EventChannel(id=cid)
            self._channels[cid] = channel
            return channel

    async def get(self, channel_id: str) -> EventChannel | None:
        async with self._lock:
            return self._channels.get(channel_id)

    async def drop(self, channel_id: str) -> None:
        async with self._lock:
            channel = self._channels.pop(channel_id, None)
        if channel is not None:
            await channel.close()

    def start_task(self, coro: Coroutine[Any, Any, Any], *, name: str) -> asyncio.Task[Any]:
        """Start and retain one background task until it completes."""
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)
        task.add_done_callback(self._on_task_done)
        return task

    async def finish(self, channel_id: str, *, retention_seconds: float = 60.0) -> None:
        """Close a channel but retain queued events briefly for late subscribers."""
        channel = await self.get(channel_id)
        if channel is not None:
            await channel.close()
            self.start_task(
                self._drop_after(channel_id, retention_seconds),
                name=f"event-channel-reap-{channel_id}",
            )

    async def _drop_after(self, channel_id: str, delay: float) -> None:
        await asyncio.sleep(delay)
        await self.drop(channel_id)

    def _on_task_done(self, task: asyncio.Task[Any]) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            _LOG.exception("background task %s failed", task.get_name(), exc_info=exc)


async def sse_stream(channel: EventChannel) -> AsyncIterator[dict[str, str]]:
    """Yield events in the shape sse-starlette expects (``{"event", "data"}``).

    Terminates after the first event whose ``phase`` is in ``TERMINAL_PHASES``,
    or after the close sentinel.
    """
    while True:
        try:
            event = await asyncio.wait_for(channel.queue.get(), timeout=300)
        except asyncio.TimeoutError:
            yield {"event": "heartbeat", "data": "{}"}
            continue

        if event.get("_close"):
            return

        phase = event.get("phase") or event.get("event")
        yield {"event": str(phase or "message"), "data": json.dumps(event)}

        if phase in TERMINAL_PHASES:
            return
