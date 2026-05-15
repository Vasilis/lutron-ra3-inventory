"""Models for LEAP request/response messages.

Vendored from pylutron-caseta v0.28.0 (Apache-2.0):
https://github.com/gurumitts/pylutron-caseta/blob/v0.28.0/src/pylutron_caseta/messages.py
"""

from __future__ import annotations

from typing import NamedTuple, Optional


class ResponseStatus:
    """A response status split into its code and message parts."""

    def __init__(self, code: Optional[int], message: str) -> None:
        self.code = code
        self.message = message

    @classmethod
    def from_str(cls, data: str) -> "ResponseStatus":
        """Convert a status-line string to a ResponseStatus."""
        space = data.find(" ")
        if space == -1:
            code: Optional[int] = None
        else:
            try:
                code = int(data[:space])
                data = data[space + 1 :]
            except ValueError:
                code = None
        return ResponseStatus(code, data)

    def is_successful(self) -> bool:
        """Check if the status code is in the range [200, 300)."""
        return self.code is not None and 200 <= self.code < 300

    def __repr__(self) -> str:
        return f"ResponseStatus({self.code!r}, {self.message!r})"

    def __str__(self) -> str:
        return f"{self.code} {self.message}"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, ResponseStatus)
            and self.code == other.code
            and self.message == other.message
        )


class ResponseHeader(NamedTuple):
    """A LEAP response header."""

    StatusCode: Optional[ResponseStatus] = None
    Url: Optional[str] = None
    MessageBodyType: Optional[str] = None
    Paging: Optional[dict] = None

    @classmethod
    def from_json(cls, data: dict) -> "ResponseHeader":
        """Convert a JSON dict to a ResponseHeader."""
        status = data.get("StatusCode")
        status_code = ResponseStatus.from_str(status) if status is not None else None
        return ResponseHeader(
            StatusCode=status_code,
            Url=data.get("Url"),
            MessageBodyType=data.get("MessageBodyType"),
            Paging=data.get("Paging"),
        )


class Response(NamedTuple):
    """A LEAP response."""

    Header: ResponseHeader
    CommuniqueType: Optional[str] = None
    Body: Optional[dict] = None

    @classmethod
    def from_json(cls, data: dict) -> "Response":
        """Convert a JSON dict to a Response."""
        return Response(
            Header=ResponseHeader.from_json(data.get("Header", {})),
            CommuniqueType=data.get("CommuniqueType"),
            Body=data.get("Body"),
        )
