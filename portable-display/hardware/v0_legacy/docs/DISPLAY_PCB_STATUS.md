# Display PCB status (KD024 / TPS65631 island)

Date: 2026-09-06 (Asia/Shanghai). Board: root `portable_display_epass.kicad_pcb`.  
`fabrication_released`: **false** (unchanged). Electrical connectivity under the current KiCad 10 rules is closed; this is not stackup, impedance, assembly, or fab approval.

## What is on the project board now

The display-completion candidate (Codex routing + one `SOC_LDO_1V8` T-junction split) replaced the 19:09 `c168cd4` island. Earlier board (display island placed, not yet routed): `verification/display_completion/pre_display_completion.kicad_pcb`.

Placement matches `tools/generate_evt1.py` `display_placement` (J4 back at the generator origin, not the earlier +4 mm shift that sealed the west QFN corridor):

| Ref | XY mm | Notes |
|---|---|---|
| J4 | 30.00, 39.00 | `Sameat:FPC45` KD024 / Molex 502598-4593 candidate land |
| U10 | 46.00, 30.00 | TPS65631DPDR, CTRL=`LCD_EN` |
| L5 / L6 | 41.50, 28.00 / 50.50, 28.00 | EL boost / IBB |
| C42–C45 | 25–32, 42.00 | VCI / VDDIO locals next to J4 |
| R29 / R31 | 30.00, 45.00 / 35.00, 42.00 | 1V8→LCD_1V8 0Ω; SWIRE 0Ω **DNP** |
| U2 | 30.00, 56.00 | unchanged |

Legacy TFT backlight `U7/L4/D4/R19/C27/C28` is **removed** from the PCB (matches schematic / `design/pin_contract.json`). Source board has no stale zone fills; refill in KiCad to inspect copper.

Copper: **2594** tracks, **440** through-vias (0.40 / 0.20 mm). In1.Cu remains GND; no extra layers.

## Routed (electrical)

All previously open display nets are one pad-island, including MIPI 1-lane, `LCD_RST` / `LCD_TE` / `LCD_EN`, EL±, VCI/VDDIO, and leftover J4 GND.

Geometric MIPI lengths on this board (not impedance-signed):

| Pair | Length | Layers |
|---|---:|---|
| `DSI_CKP` / `DSI_CKN` | 18.645 mm each | F.Cu only, 0 via |
| `DSI_D0P` / `DSI_D0N` | 19.589 mm each | F.Cu + B.Cu, 2 vias each |

`LCD_EN` is electrically closed (`U2.4` / `U8.3` / `R31.2` / `U10.7`) but is a long F/B maze (~187 mm, 22 vias). Do not treat that as a clean GPIO.

## Native check (full board, no display exceptions)

| Item | Result |
|---|---|
| KiCad | 10.0.6 |
| ERC | 0 |
| DRC violations (errors + warnings) | 0 |
| Unconnected items | 0 |
| Schematic parity | 0 |
| Unit tests | 49 passed |
| `fabrication_released` | false |

Report: `verification/native-20260906T131714Z-012dcd/status.json`. Command:

```sh
.venv/bin/python tools/verify_evt1.py --full-board --kicad-cli /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
```

Root PCB SHA-256: `1edb1ffa6b438935110cabcabe252466369eddc2f21f7d8a0532ef57d853df20`.

## Still not signed

- Manufacturer stackup, MIPI/USB/SD impedance and return path (`stackup_si`).
- Molex 502598 land pattern and TPS65631 paste/thermal (`docs/DISPLAY_FOOTPRINT_REVIEW.md`; `pinouts_footprints`).
- EL voltage / CTRL topology / panel bring-up (`display`, `bringup_firmware`).
- Power/thermal and AXP2101 variant.
- Enclosure fit of J4 at (30, 39) vs the earlier (34, 38) shift.

Release gates remain unsigned. Do **not** treat this board as fab-ready.
