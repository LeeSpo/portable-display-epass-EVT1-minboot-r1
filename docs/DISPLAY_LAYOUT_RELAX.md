# Display layout relax study

Branch: `feat/display-layout-relax` (from `feat/display-2p4-aod-rm690b0` @ `53666561e8`).

## Why

Prior tip electrically closed display nets but packed routes through the SoC pocket despite ~58×110 mm free board area (`LCD_EN` ~187 mm / 22 vias; heavy F.Cu under U2). User allows component moves for a cleaner corridor study. **Not fab-ready.**

## Intent

- Move J4 / U10 EL cluster / VCI-VDDIO parts to open a short SoC↔panel path
- Re-route MIPI 1-lane + LCD_RST/TE/EN + EL± short and mostly outside QFN top copper
- Prefer bottom/inner under packages; keep SW loops tight at U10
- Keep `fabrication_released: false`

## Status

Work in progress on this branch.
