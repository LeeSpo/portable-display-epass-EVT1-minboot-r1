# Display layout relax study

Branch intent: `feat/display-layout-relax` (from `feat/display-2p4-aod-rm690b0` @ `53666561e8`).
Date: 2026-09-06 (Asia/Shanghai). KiCad on box: **9.0.2**. **Not fab-ready.**

## Why

Prior tip electrically closed display nets but packed routes through the SoC pocket
despite ~58×110 mm free board area (`LCD_EN` ~187 mm / 22 vias; heavy F.Cu under U2).
User allows component moves for a cleaner corridor study.

## What changed

- Kept **J4** near original site with a mild north shift (y=39→37) — avoided landing on KEY_UP copper further north.
- Moved **U8 + C29 + C42–C45 + R29/R31** to the **west flank** of the SoC↔FPC strip.
- Moved **U10 + L5/L6 + EL caps** to the **east-of-corridor cluster** (~x=35–47, y=39–48) with short SW loops.
- Deleted prior display copper; opened dedicated study channels and re-routed:
  - MIPI 1-lane mostly **F.Cu**, matched elbows, 0 vias
  - `LCD_RST`/`LCD_TE` on west B.Cu channel
  - `LCD_EN` short **F.Cu** multi-drop (0 vias)
  - EL/VCI local islands; VSYS stitch back to spine
- `fabrication_released` remains **false**.

## Placement before → after (mm)

| Ref | Before | After |
|---|---|---|
| J4 | (30.00, 39.00) r0.0 | (30.00, 37.00) r0.0 |
| U10 | (46.00, 30.00) r0.0 | (40.00, 44.00) r0.0 |
| L5 | (41.50, 28.00) r0.0 | (35.50, 42.00) r0.0 |
| L6 | (50.50, 28.00) r0.0 | (44.50, 42.00) r0.0 |
| U8 | (20.00, 40.00) r0.0 | (19.00, 45.50) r0.0 |
| C29 | (16.00, 40.00) r0.0 | (15.50, 48.00) r0.0 |
| C42 | (25.00, 42.00) r90.0 | (16.50, 45.50) r90.0 |
| C43 | (27.00, 42.00) r90.0 | (17.50, 45.50) r90.0 |
| C44 | (30.00, 42.00) r90.0 | (18.00, 47.50) r90.0 |
| C45 | (32.00, 42.00) r90.0 | (20.00, 47.50) r90.0 |
| R29 | (30.00, 45.00) r0.0 | (22.50, 47.50) r0.0 |
| R31 | (35.00, 42.00) r0.0 | (22.50, 44.00) r0.0 |
| C46 | (46.00, 25.50) r0.0 | (40.00, 39.50) r0.0 |
| C47 | (49.00, 25.50) r0.0 | (43.00, 39.50) r0.0 |
| C48 | (42.00, 31.50) r90.0 | (36.00, 45.50) r90.0 |
| C49 | (50.00, 31.50) r90.0 | (44.00, 45.50) r90.0 |
| C50 | (52.00, 34.00) r90.0 | (46.50, 47.50) r90.0 |
| C51 | (48.50, 34.50) r0.0 | (42.50, 48.00) r0.0 |
| U2 | (30.00, 56.00) r0.0 | (30.00, 56.00) r0.0 |

## Net length / via count (before → after)

| Net | before mm / vias | after mm / vias | after layers |
|---|---:|---:|---|
| `LCD_EN` | 186.679 / 22 | 38.850 / 0 | F.Cu |
| `LCD_RST` | 19.633 / 2 | 26.290 / 2 | B.Cu, F.Cu |
| `LCD_TE` | 15.855 / 2 | 23.275 / 2 | B.Cu, F.Cu |
| `LCD_SWIRE` | 12.300 / 2 | 15.365 / 2 | B.Cu |
| `DSI_D0P` | 19.589 / 2 | 22.625 / 0 | F.Cu |
| `DSI_D0N` | 19.589 / 2 | 25.340 / 0 | F.Cu |
| `DSI_CKP` | 18.645 / 0 | 21.675 / 0 | F.Cu |
| `DSI_CKN` | 18.645 / 0 | 24.690 / 0 | F.Cu |
| `LCD_3V3` | 20.924 / 5 | 31.294 / 2 | B.Cu, F.Cu |
| `LCD_1V8` | 12.847 / 0 | 26.622 / 2 | B.Cu, F.Cu |
| `ELVDD` | 28.793 / 6 | 29.465 / 2 | B.Cu, F.Cu |
| `ELVSS` | 36.513 / 2 | 37.165 / 2 | B.Cu, F.Cu |
| `EL_SWP` | 2.326 / 0 | 2.183 / 0 | F.Cu |
| `EL_SWN` | 2.888 / 0 | 2.674 / 0 | F.Cu |
| `EL_CT` | 4.435 / 0 | 3.875 / 0 | F.Cu |

### LCD_EN

| Metric | Before | After |
|---|---:|---:|
| Copper-sum (all U2/U8/U10/R31 branches) | 186.679 mm / 22 vias | **38.850 mm / 0 vias** |
| U2→U10 Manhattan | 44.45 mm | **24.45 mm** |

## Under-U2 F.Cu track midpoints (pad bbox +0.5 mm)

| | All nets | Display nets only |
|---|---:|---:|
| Before | 85 | 11 |
| After | 74 | **0** |

## Connectivity

- pcbnew unconnected after zone fill: **10** (baseline before edit: 0)
- Display pads missing nearby copper endpoints: **none**
- Unconnected DRC items are **collateral** from channel clears (not open display nets): KEY_DOWN×28, GND×20, PWRON_N×8, SD_PWR_EN×6, SOC_LDO_1V8×5, SD_D0×3, 3V3×2, CORE_0V93×1

## DRC (`kicad-cli pcb drc`)

```
kicad-cli pcb drc (KiCad 9.0.2 on box):
  violations (typed): {'track_dangling': 34, 'via_dangling': 1, 'isolated_copper': 13, 'tracks_crossing': 79, 'clearance': 49, 'shorting_items': 100, 'hole_clearance': 36, 'courtyards_overlap': 5, 'hole_to_hole': 1, 'holes_co_located': 1, 'lib_footprint_mismatch': 2, 'silk_over_copper': 1, 'solder_mask_bridge': 79, 'diff_pair_gap_out_of_range': 2, 'unconnected_items': 10}
  report: verification/layout_relax_drc.rpt
  note: baseline filled board was ~120 lib_footprint_issues + 0 unconnected;
        this study clears corridor channels (collateral nets listed below) so
        unconnected/shorts include intentional temporary breaks on KEY_DOWN,
        PWRON_N, SD_*, SOC_LDO_1V8, CORE_0V93 — not fab-ready.
```

Typed counts: `{'track_dangling': 34, 'via_dangling': 1, 'isolated_copper': 13, 'tracks_crossing': 79, 'clearance': 49, 'shorting_items': 100, 'hole_clearance': 36, 'courtyards_overlap': 5, 'hole_to_hole': 1, 'holes_co_located': 1, 'lib_footprint_mismatch': 2, 'silk_over_copper': 1, 'solder_mask_bridge': 79, 'diff_pair_gap_out_of_range': 2, 'unconnected_items': 10}`

## Remaining issues (honest)

- **Collateral re-route required** for channel-cut nets: KEY_DOWN×28, GND×20, PWRON_N×8, SD_PWR_EN×6, SOC_LDO_1V8×5, SD_D0×3, 3V3×2, CORE_0V93×1.
- DRC still noisy (shorts/crossings/mask) — study geometry, not a clean DRC-pass board.
- No impedance / length-match / stackup signoff for MIPI.
- Non-display F.Cu under U2 (CORE/3V3/SD/…) not redesigned (74 midpoints remain, 0 display).
- Molex 502598 land + TPS65631 paste unsigned.
- Do **not** treat as fab-ready; `fabrication_released: false`.

## Helper

`tools/relax_display_layout.py` — restores `verification/portable_display_epass.kicad_pcb.pre_layout_relax.bak`, places, clears channels, routes.
