# LEAP protocol notes — RadioRA 3

These notes describe request/response shapes handled by the extractor and observations from previous compatibility testing. **The surface area changes across processor firmware versions**; verify behavior on the firmware you target. These observations are not a vendor guarantee or a current-device acceptance test.

## Connection

- **Pairing port:** TCP 8083, TLS with the Lutron LAP CA bundled into every Caseta/RA3 device and the official Lutron app. On RA 3 the handshake falls back to the Lutron root CA on first verification error (auto-detected).
- **Production LEAP port:** TCP 8081, TLS, mutual auth.
- The transport passes an empty `server_hostname` and requires certificate-chain verification. Pairing may fall back to a vendor-wide Lutron root CA; that is not a unique processor certificate pin. Review trust and processor identity binding before reusing this transport in another application.
- Connection refusal has been observed while another integration was attached. The app surfaces an `AlreadyConnectedError`; this is an observed compatibility limitation, not a universal LEAP single-client guarantee.

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

Previous compatibility testing on the 26.x firmware family showed these differences from older response shapes:

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

## Observed compatibility limitations

- **Preset assignment data is not exposed.** `/preset/{id}` returns only `{href, Parent}` — every `*Assignments` array is empty, no zone-or-level data. Neither does any sub-URL we've probed (`/preset/{id}/dimmedlevelassignment` returns 204 No Content). The "press button N → dim zone X to 80%" mapping is reachable through the Designer file but not over LEAP on this firmware. We capture the PM type (toggle / single-action / raise / lower) and the engraving text, which still answers "what does this button do?" at a glance.
- **`/areascene`, `/virtualbutton`, `/system/away/1/status` return "not supported".** Until we find their replacements, M1's snapshot will show empty counts for these.

If you have a different RA 3 firmware that DOES expose preset assignments, please open an issue with the firmware family and a minimal synthetic or manually reviewed response shape. Do not post raw household exports, credentials, private addresses, serials, engravings, or device/room names. A minimal fixture can help us add a compatibility shim.

## Public examples

`examples/sanitized-snapshot.json` and its generated Markdown are deliberately synthetic fixtures. Their topology, identifiers, names, timestamps, and versions do not describe an installed system. Use them to explore the app and exports, not as evidence that a particular processor or firmware supports these requests.
