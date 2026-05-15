# Legacy scripts

These are the standalone Python scripts that this project grew out of. They are kept here as historical reference and for fixture replay; **the canonical extraction code now lives at `backend/src/ra3_inventory/leap/extract.py`** and is what production builds use.

| File | What it is |
|---|---|
| `lutron_raw_extract.py` | The canonical raw-LEAP extractor. Drives `pylutron_caseta`'s private `bridge._leap` to read every relevant endpoint and resolve the full device → button → programming-model → preset graph. **This is the one that was ported.** |
| `lutron_extract.py` | Older library-based extractor using `pylutron-caseta`'s parsed API. Drops shade SKUs, firmware, and button programming. Reference only. |
| `lutron_raw_devices.py` | Early raw-LEAP shade probe. Reference only. |
| `sanitize_inventory.py` | Strips serials, MAC addresses, and IPs from an inventory JSON. Will be ported to `scripts/sanitize-snapshot.py` for the new app. |
| `legacy-scripts-README.md` | The original standalone-CLI README. |

Once the new app's M1 is fully verified end-to-end against the user's RA 3, these can be deleted from the tree — the canonical history is in git.
