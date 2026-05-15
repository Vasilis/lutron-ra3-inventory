"""LEAP protocol layer.

Vendored from pylutron-caseta v0.28.0 (Apache-2.0):
https://github.com/gurumitts/pylutron-caseta

The pairing handshake, TLS connection setup, and LEAP request/response transport
are reused with minimal changes. The high-level ``Smartbridge`` parsed API is
intentionally NOT vendored; this app drives raw LEAP requests against the
processor to preserve information that the parsed API discards (shade SKUs,
firmware versions, button programming, RA3-specific endpoints).

See THIRD_PARTY_LICENSES/pylutron-caseta-LICENSE for the upstream license text.
"""

from .client import AlreadyConnectedError, extract_inventory
from .errors import BridgeDisconnectedError, BridgeResponseError
from .extract import DEVICE_ENDPOINTS, TOPLEVEL_ENDPOINTS, InventoryExtractor
from .messages import Response, ResponseHeader, ResponseStatus
from .pairing import PairingData, async_pair
from .protocol import LeapProtocol, id_from_href, open_connection
from .transport import connect_leap

__all__ = [
    "DEVICE_ENDPOINTS",
    "TOPLEVEL_ENDPOINTS",
    "AlreadyConnectedError",
    "BridgeDisconnectedError",
    "BridgeResponseError",
    "InventoryExtractor",
    "LeapProtocol",
    "PairingData",
    "Response",
    "ResponseHeader",
    "ResponseStatus",
    "async_pair",
    "connect_leap",
    "extract_inventory",
    "id_from_href",
    "open_connection",
]
