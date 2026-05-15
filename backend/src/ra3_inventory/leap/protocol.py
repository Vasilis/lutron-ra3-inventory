"""LEAP request/response protocol over an asyncio stream.

Vendored from pylutron-caseta v0.28.0 (Apache-2.0):
https://github.com/gurumitts/pylutron-caseta/blob/v0.28.0/src/pylutron_caseta/leap.py

Modified: imports adjusted to the local leap/ namespace (errors, messages).
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Callable, Dict, List, Optional, Tuple

import orjson

from .errors import BridgeDisconnectedError
from .messages import Response

_LOG = logging.getLogger(__name__)
_DEFAULT_LIMIT = 2**18


def _make_tag() -> str:
    return str(uuid.uuid4())


class LeapProtocol:
    """Make request/response/subscribe calls over a LEAP stream."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer
        self._in_flight_requests: Dict[str, "asyncio.Future[Response]"] = {}
        self._tagged_subscriptions: Dict[str, Callable[[Response], None]] = {}
        self._unsolicited_subs: List[Callable[[Response], None]] = []

    async def request(
        self,
        communique_type: str,
        url: str,
        body: Optional[dict] = None,
        tag: Optional[str] = None,
        paging: Optional[dict] = None,
    ) -> Response:
        """Make a request to the bridge and return the response."""
        if tag is None:
            tag = _make_tag()

        future: asyncio.Future = asyncio.get_running_loop().create_future()

        cmd: dict = {
            "CommuniqueType": communique_type,
            "Header": {"ClientTag": tag, "Url": url},
        }
        if paging is not None:
            cmd["Header"]["Paging"] = paging
        if body is not None:
            cmd["Body"] = body

        self._in_flight_requests[tag] = future

        def clean_up(fut: asyncio.Future) -> None:
            if fut.cancelled():
                self._in_flight_requests.pop(tag, None)

        future.add_done_callback(clean_up)

        try:
            text = orjson.dumps(cmd)
            _LOG.debug("sending %s", text)
            self._writer.writelines((text, b"\r\n"))
            return await future
        finally:
            self._in_flight_requests.pop(tag, None)

    async def run(self) -> None:
        """Event monitoring loop. Run until the stream is at EOF."""
        while not self._reader.at_eof():
            received = await self._reader.readline()
            if received == b"":
                break

            resp_json = orjson.loads(received)
            if not isinstance(resp_json, dict):
                continue

            tag = resp_json.get("Header", {}).pop("ClientTag", None)
            if tag is not None:
                in_flight = self._in_flight_requests.pop(tag, None)
                if in_flight is not None and not in_flight.done():
                    _LOG.debug("received: %s", resp_json)
                    in_flight.set_result(Response.from_json(resp_json))
                else:
                    subscription = self._tagged_subscriptions.get(tag)
                    if subscription is not None:
                        _LOG.debug("received for subscription %s: %s", tag, resp_json)
                        subscription(Response.from_json(resp_json))
                    else:
                        _LOG.error("Unexpected tag %s: %s", tag, resp_json)
            else:
                _LOG.debug("Untagged message: %s", resp_json)
                obj = Response.from_json(resp_json)
                for handler in self._unsolicited_subs:
                    try:
                        handler(obj)
                    except Exception:  # noqa: BLE001
                        _LOG.exception("unsolicited message handler raised")

    async def subscribe(
        self,
        url: str,
        callback: Callable[[Response], None],
        body: Optional[dict] = None,
        communique_type: str = "SubscribeRequest",
        tag: Optional[str] = None,
    ) -> Tuple[Response, str]:
        """Subscribe to events on a URL. The callback receives further responses with the same tag."""
        if not callable(callback):
            raise TypeError("callback must be callable")
        if tag is None:
            tag = _make_tag()

        response = await self.request(communique_type, url, body, tag=tag)
        status = response.Header.StatusCode
        if status is not None and status.is_successful():
            self._tagged_subscriptions[tag] = callback
            _LOG.debug("Subscribed to %s as %s", url, tag)
        return response, tag

    def subscribe_unsolicited(self, callback: Callable[[Response], None]) -> None:
        """Register a callback for untagged response messages."""
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._unsolicited_subs.append(callback)

    def unsubscribe_unsolicited(self, callback: Callable[[Response], None]) -> None:
        self._unsolicited_subs.remove(callback)

    def close(self) -> None:
        """Disconnect and fail every in-flight request."""
        self._writer.close()
        for request in self._in_flight_requests.values():
            if not request.done():
                request.set_exception(BridgeDisconnectedError())
        self._in_flight_requests.clear()
        self._tagged_subscriptions.clear()

    async def wait_closed(self) -> None:
        await self._writer.wait_closed()


async def open_connection(
    host: str, port: int, *, limit: int = _DEFAULT_LIMIT, **kwargs
) -> LeapProtocol:
    """Open an asyncio stream and wrap it in a LeapProtocol."""
    reader, writer = await asyncio.open_connection(host, port, limit=limit, **kwargs)
    return LeapProtocol(reader, writer)


_HREFRE = re.compile(r"/(?:\D+)/(\d+)(?:/\D+)?")


def id_from_href(href: str) -> str:
    """Extract the numeric ID from any LEAP href."""
    match = _HREFRE.match(href)
    if match is None:
        raise ValueError(f"Cannot find ID from href {href!r}")
    return match.group(1)
