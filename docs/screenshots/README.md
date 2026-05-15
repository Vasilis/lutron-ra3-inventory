# Screenshots

This directory holds UI screenshots embedded in the project README and the
release notes. PNG / WebP / GIF only — keep individual files under 500 KB
where possible so cloning the repo stays fast.

## Planned set (M1)

- `welcome.png` — first-launch welcome screen with the "Pair a processor"
  call to action.
- `pairing.png` — pairing dialog mid-flow, prompting the user to press the
  physical button on the front of the RA3.
- `extracting.png` — extraction toast with the live progress counter
  (areas / devices / zones / keypads).
- `browser.png` — three-pane inventory browser: area tree on the left,
  grouped device list in the middle, keypad detail with button programming
  on the right.
- `export.png` — export dialog with the Recovery / Technical / Share-safe
  preset row, format buttons, section checkboxes, and the inline Markdown
  preview.
- `firmware-badge.png` — close-up of the gear icon with the iMessage-style
  amber badge counting devices that have a firmware update available.

## How to capture

On macOS, `Cmd+Shift+5 → Capture Selected Window` against the running app
window gives a clean, drop-shadowed PNG. Drop the file in this directory
and reference it from the root `README.md` as
`![alt](docs/screenshots/<name>.png)`.

## Privacy

Snapshots in the running app contain real area names, device serials, MAC
addresses, and host IPs. Before committing a screenshot:

- Switch to the **Share-safe** export preset and re-extract, or
- Run `python scripts/sanitize_snapshot.py` on a saved snapshot and load
  that into the app, or
- Crop / blur identifying text in the image editor of your choice.

Anything visibly identifying your processor or home shouldn't land in this
public repo.
