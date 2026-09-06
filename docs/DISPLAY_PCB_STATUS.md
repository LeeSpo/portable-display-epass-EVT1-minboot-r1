# Display PCB status (KD024 / TPS65631 island)

Date: 2026-09-06 (Asia/Shanghai). Board: `portable_display_epass.kicad_pcb` on this tree (not a full-history clone).  
`fabrication_released`: **false** (unchanged).

## What changed

### Connector / nets
- **J4** footprint swapped **FPC20 → `Sameat:FPC45`**, value `KD024EGOIN152-01`, placed at **(34.00, 38.00) mm** (shifted +4 mm X vs old TFT FPC20 at 30,39 to reduce clash with U8).
- Pad nets assigned from current schematic/netlist: ELVSS 3–4, ELVDD 6–7, LCD_3V3 9, LCD_1V8 11, LCD_TE1 13, LCD_SWIRE 14, LCD_TE 15, LCD_RST 16, DSI_D0P/N 35/36, DSI_CKP/N 39/40, IM0/IM1/MTP + many pins → GND; pins 18–29 NC (no net).
- **U2 pad 3** net renamed **LCD_PWM → LCD_TE**.

### EL bias island (new)
| Ref | Footprint | Value | XY mm | Notes |
|---|---|---|---|---|
| U10 | Sameat:WSON-12 | TPS65631DPDR | 46.00, 32.50 | CTRL=LCD_EN |
| L5 | Sameat:IND_2x2 | 4.7uH | 39.50, 28.00 | VSYS–EL_SWP (footprint; SW copper ratsnest) |
| L6 | Sameat:IND_2x2 | 4.7uH | 53.00, 31.50 | EL_SWN–GND (footprint; SW copper ratsnest) |
| C46/C47 | 0603 | 10u | 47.50/50.50, 26.50 | VIN near PVIN/AVIN |
| C48 | 0603 | 10u | 41.50, 34.50 | ELVDD Cout (local copper to U10 OUTP) |
| C49/C50 | 0603 | 10u | 50.00,35.00 / 53.00,33.00 | ELVSS Cout |
| C51 | 0402 | 100n | 49.50, 36.80 | CT |

### VCI / VDDIO
| Ref | XY mm | Role |
|---|---|---|
| C42/C43 | 48.00/50.00, 41.00 | LCD_3V3 local |
| R29 | 52.00, 41.00 | 1V8→LCD_1V8 0Ω |
| C44/C45 | 48.00/50.00, 43.50 | LCD_1V8 local |
| R31 | 52.00, 43.50 | **DNP** SWIRE option |

### DNP TFT backlight (parked, nets cleared)
U7/L4/D4/R19/C27/C28 moved near **(52, 5…24)** and marked DNP / exclude-from-pos. Not for KD024 AMOLED.

### Copper intentionally cleared
Tracks/vias under the new J4 courtyard and the old backlight pocket (~40–54 × 27–37.5 mm) were deleted so FPC45/U10 could land. Some non-display routes that crossed that pocket were sacrificed and need restore/re-route later.

## What is routed vs ratsnest

| Net group | Status |
|---|---|
| U10 OUTP/FBS ↔ C48 (ELVDD), OUTN ↔ C49/C50 (ELVSS), CT ↔ C51 | **Local island copper present** |
| U10 PVIN/AVIN ↔ C46/C47 VSYS stitch | **Partial local copper** |
| L5 EL_SWP / L6 EL_SWN short loops | **Footprints placed; SW copper left as ratsnest** after shorts against VSYS in dense pocket |
| ELVDD/ELVSS / LCD_3V3 / LCD_1V8 → J4 | **Mostly ratsnest** (J4 stubs removed to avoid SD/KEY shorts) |
| MIPI D0/CLK, LCD_RST, LCD_TE, LCD_EN to U2 | **Ratsnest only** — SoC/SD/KEY corridors too dense for blind F/B manhattan without a full rip-up |
| U8 → LCD_3V3 / U10 CTRL | **Incomplete** |

Zones were refilled after edits.

## FPC45 land pattern

`sameat.pretty/FPC45.kicad_mod` remains a **generator 0.5 mm pitch placeholder** for Molex **502598-4591** (not a manufacturer LP). Pads narrowed to **0.28×1.40 mm**, courtyard/silk pin-1 mark improved. Expect residual **solder_mask_bridge** warnings until a real Molex LP is dropped in. Documented for fab gate `pinouts_footprints`.

## DRC / parity (honest)

See `verification/display_island_drc.rpt`, `verification/display_island_drc_cli.log`, `verification/display_island_drc_summary.txt`.

| Metric | Pre-edit (baseline) | Post-edit |
|---|---:|---:|
| Copper DRC violations (`--severity-error`) | **0** | **7** |
| Unconnected items | **162** | **81** |
| Schematic parity issues | (not run pre) | **27** |

Unconnected count improved vs raw pre-edit CLI (162→81) largely from zone fill + net assignment + clearing orphan backlight connectivity, **not** because display→SoC is finished. New DRC errors are expected from FPC45 mask geometry, courtyard packing, and copper clearances against remaining neighbors after pocket delete.

Blockers for “full display route”:
1. Re-route SD/KEY/WAKE copper deleted under the island pocket.
2. Length-matched MIPI 1-lane + LCD_RST/TE/EN on a planned layer pair with stackup.
3. Complete EL± and VCI feeds to J4 without crossing the pad row.
4. Replace FPC45 with manufacturer land pattern; resolve mask bridges.
5. ERC/DRC clean + parity before any fab release.

## Files touched

- `portable_display_epass.kicad_pcb`
- `sameat.pretty/FPC45.kicad_mod`
- `tools/update_display_island_pcb.py`
- `design/release_gates.json` (evidence only; fabrication_released still false)
- `docs/DISPLAY_PCB_STATUS.md` (this file)
- `verification/display_island_drc.rpt`
- `verification/display_island_drc_cli.log`
- `verification/display_island_drc_summary.txt`
- `verification/portable_display_epass.kicad_pcb.pre_display_island.bak` (pre-edit backup)

Do **not** treat this board as fab-ready.
