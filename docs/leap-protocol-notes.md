# LEAP protocol notes — RadioRA 3 (verified)

These are the LEAP request/response shapes this app actually issues and parses, validated against a live RA 3 processor. The single most important thing to know is that **the surface area changes meaningfully across processor firmware versions**, so test against the firmware you're targeting.

## Connection

- **Pairing port:** TCP 8083, TLS with the Lutron LAP CA bundled into every Caseta/RA3 device and the official Lutron app. On RA 3 the handshake falls back to the Lutron root CA on first verification error (auto-detected).
- **Production LEAP port:** TCP 8081, TLS, mutual auth.
- **Hostname verification is disabled** (`server_hostname=""`). The processor's leaf cert uses a serial-derived CN, not a DNS name. Identity comes from the pinned CA cert returned by pairing.
- **Only one client at a time.** TLS handshake fails with `ConnectionRefusedError` if Home Assistant, HomeBridge, or another LEAP client is already attached. Our `AlreadyConnectedError` surfaces this with a useful message.

## Wire format

JSON over TLS, newline-delimited. Each message has a `Header`, optional `Body`, and a `CommuniqueType`. Requests carry a `ClientTag` (UUID), and the matching response echoes it back. Subscriptions reuse the same tag for unsolicited updates.

The vendored `LeapProtocol` (from pylutron-caseta) handles dispatch.

## Endpoints we hit (M1)

| URL | Purpose | Notes |
|---|---|---|
| `/project` | Project metadata | `ProductType: "Lutron RadioRA 3 Project"`; `ProjectModifiedTimestamp` is either an ISO8601 string (older firmware) or a `{Year,Month,Day,Hour,Minute,Second,Utc}` dict (26.x+) |
| `/server/1` | Server metadata | |
| `/device?where=IsThisDevice:true` | The processor itself | Bare `/device` returns 204 on RA 3 — must use the where-filter |
| `/device?where=IsThisDevice:false` | All other devices | |
| `/device/{id}` | A single device, full fields | |
| `/device/{id}/buttongroup/expanded` | A keypad's buttons inline with their `ProgrammingModel` references | The **only** way to enumerate buttons on RA 3 firmware 26.x+ |
| `/zone/{id}` | One zone definition (ControlType, Category, Name, AssociatedArea) | |
| `/area` | All areas (flat list with `Parent.href`) | |
| `/programmingmodel/{id}` | What happens on press/release/etc. | Schema varies — see below |
| `/preset/{id}` | Target state for a PM action | **Often returns only `{href, Parent}` on firmware 26.x+** (see Known limitations) |

## Firmware drift

The user's original brief was accurate for older firmware. The processor we validated against runs **26.03.12f000** and exhibits real API changes:

1. **Bulk endpoints disappear.** Bare `/zone`, `/button`, `/buttongroup`, `/led`, `/areascene`, `/virtualbutton` all return `400 BadRequest: "This request is not supported"`. Discovery has to walk references from `/device?where=IsThisDevice:false` instead:
   - Zones: union of every device's `LocalZones[].href`, fetched individually as `/zone/{id}`.
   - Buttons: per-device `/device/{id}/buttongroup/expanded`.
   - LEDs / area scenes / virtual buttons / timeclock rules: gracefully empty until we find a working RA 3 endpoint.

2. **Devices lose their `ButtonGroups` field.** Older firmware annotated each keypad/pico device with `ButtonGroups: [{href: ...}]`; 26.x doesn't. Detect keypad-like devices by `DeviceType` instead (see `KEYPAD_DEVICE_TYPES` in `backend/src/ra3_inventory/leap/extract.py`).

3. **`FirmwareImage.Firmware.DisplayName` is null.** The real version moved to `FirmwareImage.Contents[0].OS.Firmware.DisplayName`. Our `_firmware_display()` helper checks both locations.

4. **`ProgrammingModel` uses new schemas.** The legacy `PressOnPresetAssignments[]` / `ReleaseOnPresetAssignments[]` / etc. fields are all `null` on this firmware. New shapes:
   - `AdvancedToggleProgrammingModel`: `AdvancedToggleProperties.{Primary,Secondary}Preset.href` — primary vs. secondary toggle state.
   - `SingleActionProgrammingModel`: `Preset.href`.
   - `SingleSceneRaiseProgrammingModel` / `SingleSceneLowerProgrammingModel`: `Preset.href` plus a `Direction` field.

   Our preset href collector walks any PM dict tree looking for `href` keys starting with `/preset/`, so it stays robust against future schema additions.

## Known limitations on firmware 26.03.12f000

- **Preset assignment data is not exposed.** `/preset/{id}` returns only `{href, Parent}` — every `*Assignments` array is empty, no zone-or-level data. Neither does any sub-URL we've probed (`/preset/{id}/dimmedlevelassignment` returns 204 No Content). The "press button N → dim zone X to 80%" mapping is reachable through the Designer file but not over LEAP on this firmware. We capture the PM type (toggle / single-action / raise / lower) and the engraving text, which still answers "what does this button do?" at a glance.
- **`/areascene`, `/virtualbutton`, `/system/away/1/status` return "not supported".** Until we find their replacements, M1's snapshot will show empty counts for these.

If you have a different RA 3 firmware that DOES expose preset assignments, please open an issue — including the firmware version, the `/preset/{id}` response body, and (if possible) a sanitized `lutron_raw.json`. Comparing against a known-good fixture will let us add a back-compat shim.

## Live validation on the maintainer's home

Last full run against `192.168.1.184` (firmware 26.03.12f000):

| Category | Count |
|---|---:|
| Areas | 11 |
| Devices (excl. processor) | 50 |
| Zones | 40 |
| Buttons | 110 |
| ProgrammingModels | 88 |
| Presets (stub bodies only) | 141 |
| Duration | 7.3 s |

Sanitized snapshot from this run lives at `examples/sanitized-snapshot.json` — it's what the M1 frontend tests will render against, and what fresh contributors can diff their own setups against.
