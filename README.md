# lutron-ra3-inventory

> Polished open-source desktop app for browsing a Lutron RadioRA 3 (and HomeWorks QSX) inventory over LEAP — areas, devices, zones, keypads with full button programming, firmware versions, and shade SKUs. macOS first.

**Status:** pre-alpha — M1 in active development. Not yet installable.

## Why

The [community `pylutron-caseta` library](https://github.com/gurumitts/pylutron-caseta) exposes a parsed API that's great for home-automation integration but lossy as an inventory: every shade collapses to `type="Shade"` with `model=None`, button programming is invisible, and RA3-specific endpoints (`/areascene`, `/project/timeclockeventrules`, `/virtualbutton`) are skipped. Integrators and homeowners who want a faithful picture of their system have to drop to raw LEAP requests.

This app does that for you, behind a UI.

## What you'll get (when M1 ships)

- One-click pair with your RA 3 / QSX processor (with the obligatory 30-second button-press dance)
- Full raw-LEAP extraction — every device, zone, keypad, button, shade, firmware version, programming model, preset, area scene, timeclock rule
- Three-pane browser: areas tree → device list → device detail (with all fields)
- Snapshots saved locally; browse the inventory even when the processor is unreachable
- Export to JSON / Markdown / CSV / Excel
- Credentials stored in macOS Keychain

## Planned (M2+)

- Live state (zone levels, occupancy, LEDs) via processor subscriptions
- Control surface (`GoToLevel`, virtual button presses, area scene recall)
- Diff mode (baseline vs current snapshot — see what changed after a Designer push)
- Multi-processor support
- Windows + Linux

## Architecture

| Layer | Choice |
|---|---|
| Backend | Python 3.10+ · FastAPI · Pydantic v2 |
| LEAP | Vendored pairing + TLS + LEAP transport from pylutron-caseta (Apache-2.0) |
| Frontend | React 18 · Vite · TypeScript (strict) · Tailwind · shadcn/ui |
| Shell | PyWebView (WKWebView on macOS) |
| Packaging | `briefcase` → codesigned + notarized `.app` (universal2) |

Realtime in M1 is SSE-only; WebSockets are deferred to M2 because of known WKWebView `ws://127.0.0.1` issues.

See [`docs/architecture.md`](docs/architecture.md) for the long version and [`docs/leap-protocol-notes.md`](docs/leap-protocol-notes.md) for the verified LEAP endpoint surface against RA 3 firmware.

## Repo layout

```
backend/         FastAPI + LEAP extractor + PyWebView entry
frontend/        React UI
docs/            architecture, protocol notes, screenshots, legacy scripts
examples/        sanitized sample snapshot (no real serials/MACs)
scripts/         dev mock server, OpenAPI/TS client gen, build helpers
.github/         CI workflows + issue/PR templates
```

## Development

Requirements: macOS, Python 3.10+, Node 20+, `npm` or `pnpm`.

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest

# Frontend
cd ../frontend
npm install
npm run dev      # Vite dev server on :5173

# Run the whole app (backend serves frontend dist + opens webview)
cd ..
./scripts/dev-run.sh
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for coding standards and PR workflow.

## Pairing

On first launch the app opens a wizard. When prompted, **walk to your RA 3 processor and press the small black button on the front** within 30 seconds. The app stores the resulting key + cert in your macOS Keychain.

If you already have pairing certs from another tool (e.g., the standalone `lutron_raw_extract.py` script this project grew out of), drop them into `~/Library/Application Support/RA3Inventory/profiles/<serial>/certs/` — the app will pick them up.

Only **one** LEAP client can be connected to a processor at a time. If you also run Home Assistant or HomeBridge with a LEAP integration, close it before pairing or extracting.

## Security

- Private keys are stored in the macOS Keychain by default; the encrypted on-disk fallback uses Fernet over a scrypt-derived key gated by a user passphrase.
- LEAP traffic is TLS, but the processor's CA is self-signed by Lutron — that's why we pin the bridge cert alongside our client cert.
- Snapshots may contain device serials, MAC addresses, and network info. The default export to JSON/CSV/XLSX includes these; use the "sanitized" export option to strip them before sharing.

## License

Apache-2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

## Trademarks

Lutron, RadioRA, RadioRA 3, Sunnata, Pico, Caseta, Palladiom, Sivoia, Ketra, and Serena are trademarks of Lutron Electronics Co., Inc. This project is not affiliated with, endorsed by, or sponsored by Lutron.
