# Lutron RadioRA3 Inventory Extractor

Pairs with a Lutron RA3 processor over LEAP, then dumps every available
device, area, keypad button, and occupancy group to a Markdown report
(`lutron_inventory.md`) plus a raw `lutron_inventory.json` for completeness.

Verified against `pylutron-caseta` 0.28.0 on Python 3.10+.

## Setup (one-time)

```bash
cd /path/to/this/folder
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install 'pylutron-caseta>=0.28.0'
```

## Run

```bash
python lutron_extract.py --host 192.168.1.184
```

The first run will prompt you to press the small black button on the front
of the RA3 processor. Do it within ~30 seconds. Pairing cert files are
cached in `./lutron_certs/`, so subsequent runs skip pairing.

### Options
- `--host 192.168.1.184` — processor IP (default shown)
- `--certs-dir ./lutron_certs` — where to keep the three PEM files
- `--out-dir .` — where to write the `.md` and `.json`
- `--force-pair` — re-pair even if certs exist (use after factory reset or
  if certs were revoked)

## Output

| File | Purpose |
|---|---|
| `lutron_inventory.md` | Human-readable report grouped by area, with summary table at top |
| `lutron_inventory.json` | Full raw dump (every field returned by the LEAP API) |
| `lutron_certs/caseta-bridge.crt` | CA cert from the processor |
| `lutron_certs/caseta.crt` | Client cert for this app |
| `lutron_certs/caseta.key` | Private key — **keep secret**, mode 0600 |

## What's captured

- **Areas**: id, name, parent_id, full path
- **Devices**: id, name, type, model, serial (where reported), zone,
  area, parent_device, control_station_name, button_groups
- **Buttons** (keypads, picos, scene buttons): id, button_number,
  button_group, button_name, engraved name, type, model, serial,
  button_led, parent_device
- **Occupancy groups**: id, name, area, status, sensors

## Known gaps (RA3-specific)

- **Serial numbers**: KeypadLEDs and some keypads return `null` for
  `serial`. The factory-printed serial is fully reliable only in the
  Designer/Essentials project file.
- **Scenes**: `pylutron-caseta` does **not** load scenes on the RA3 code
  path (the `_load_scenes` step is Caseta-only). Scene buttons still
  appear under their parent keypad in the Buttons section.
- **Timeclock / Smart Away**: not exposed by `pylutron-caseta`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Connection refused` during pairing | Check the IP is reachable: `nc -vz 192.168.1.184 8083` |
| Pairing hangs at "Press the button" | You have ~30s after the prompt; re-run if you missed it |
| `SSLCertVerificationError` on connect | Certs went stale — re-run with `--force-pair` |
| `Address already in use` | Another LEAP client is connected. Close it (HA, HomeBridge plugin, etc.) and retry |

## Security notes

- The `caseta.key` file is an authenticated identity to your processor.
  Treat it like an SSH private key. The script chmods it to 0600 on
  POSIX systems.
- LEAP traffic is TLS, but the processor's CA is self-signed by Lutron —
  that's why we keep `caseta-bridge.crt` alongside the cert/key.
