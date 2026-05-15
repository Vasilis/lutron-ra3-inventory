"""LEAP error types.

Vendored from pylutron-caseta v0.28.0 (Apache-2.0):
extracted from ``pylutron_caseta/__init__.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .messages import Response, ResponseStatus


class BridgeDisconnectedError(Exception):
    """Raised when the connection is lost while waiting for a response."""


class BridgeResponseError(Exception):
    """Raised when the bridge sends an error response."""

    def __init__(self, response: "Response") -> None:
        super().__init__(str(response.Header.StatusCode))
        self.response = response

    @property
    def code(self) -> Optional["ResponseStatus"]:
        """Get the status code returned by the server."""
        return self.response.Header.StatusCode
