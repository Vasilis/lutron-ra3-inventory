# Lutron Inventory — 192.0.2.1

**Project:** Synthetic Inventory Example — Not a Real Installation  
**ProductType:** `Synthetic LEAP Fixture`  
**Project Modified:** 2000-01-01T00:00:00Z  
**Extracted at:** 2000-01-01T00:00:00+00:00  
**Schema:** v1

## Processor

| Field | Value |
|---|---|
| Name | Synthetic Processor |
| DeviceType | `RadioRa3Processor` |
| ModelNumber | SYNTHETIC-PROCESSOR |
| SerialNumber | ? |
| Firmware | synthetic-1.0 |
| MAC | ? |

## Summary

| Category | Count |
|---|---:|
| Areas | 3 |
| Devices (excl. processor) | 3 |
| Zones | 2 |
| Buttons | 2 |
| LEDs | 0 |
| Virtual buttons | 0 |
| Area scenes | 0 |
| ProgrammingModels resolved | 2 |
| Presets resolved | 2 |

## Device Type x Model

| Count | DeviceType | ModelNumber |
|---:|---|---|
| 1 | `SunnataDimmer` | SYNTHETIC-DIMMER |
| 1 | `SunnataKeypad` | SYNTHETIC-KEYPAD |
| 1 | `SunnataSwitch` | SYNTHETIC-SWITCH |

## Areas

| Area | Full path |
|---|---|
| Synthetic Site | Synthetic Site |
| Demo Area A | Synthetic Site > Demo Area A |
| Demo Area B | Synthetic Site > Demo Area B |

## Devices by Area

### Synthetic Site > Demo Area A

| Name | Type | Model | Serial | Firmware |
|---|---|---|---|---|
| Demo Device A | SunnataDimmer | SYNTHETIC-DIMMER | _(none)_ | synthetic-1.0 |
| Demo Keypad | SunnataKeypad | SYNTHETIC-KEYPAD | _(none)_ | synthetic-1.0 |

### Synthetic Site > Demo Area B

| Name | Type | Model | Serial | Firmware |
|---|---|---|---|---|
| Demo Device B | SunnataSwitch | SYNTHETIC-SWITCH | _(none)_ | synthetic-1.0 |

## Zones

| Zone | Control type | Controlling device |
|---|---|---|
| Demo Load A | Dimmed | Demo Device A |
| Demo Load B | Switched | Demo Device B |

## Keypads — Button Engravings

_The button labels you'll need to recreate after a factory reset. Re-program each button's actions in Lutron Designer._

| Keypad | Area | Model | Button engravings |
|---|---|---|---|
| Demo Keypad | Synthetic Site > Demo Area A | SYNTHETIC-KEYPAD | 1=DEMO A, 2=DEMO B |

