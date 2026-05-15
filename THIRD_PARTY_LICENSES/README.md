# Third-party licenses

This directory contains the verbatim license texts of third-party software vendored into this project. Apache-2.0 §4(b) requires these to be reproduced when distributing modified or unmodified Apache-2.0-licensed work.

| Vendored from | License file | Files |
|---|---|---|
| [pylutron-caseta](https://github.com/gurumitts/pylutron-caseta) v0.28.0 | `pylutron-caseta-LICENSE` | `backend/src/ra3_inventory/leap/{__init__,_const,assets,errors,messages,pairing,protocol,transport,utils}.py` |

Vendored source files carry per-file headers identifying their origin, version, and any modifications. `leap/transport.py` is a new module assembled from snippets of pylutron-caseta's `smartbridge.py` (the parsed Smartbridge API itself is intentionally **not** vendored — this app drives raw LEAP requests directly).
