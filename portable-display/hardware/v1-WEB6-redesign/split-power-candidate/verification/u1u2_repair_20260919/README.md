# U1 / U2 repair checkpoints — 2026-09-19

Completed 2026-09-20: validated repair promoted to the main split-power candidate and QFN libraries. Native KiCad DRC: 0 violations, 0 unconnected. Matching final audit: `final_audit.json`. Intermediate numbered checkpoints are historical WIP and must not be used for fabrication. Original candidate is `original.kicad_pcb`; complete pre-promotion backups are in `before_promotion/`. The final candidate still requires assembly and system qualification.

Scope: split-power-candidate only; U1 AXP2101 / U2 V851S land pattern, associated routing and project-local QFN library. C38 moved from (25.50,55.35) to (25.50,55.75), angle -90° unchanged; all other placements retained. Numbered pad net assignments, board shape and project rules retained.

| | U1 | U2 |
|---|---|---|
| Body | 5 × 5 mm | 9 × 9 mm |
| Pitch | 0.40 mm | 0.35 mm |
| Radial pad center | ±2.40 mm | ±4.40 mm |
| Peripheral copper, length × width | 0.70 × 0.20 mm | 0.70 × 0.18 mm |
| Exposed pad copper | 3.40 × 3.40 mm | 6.50 × 6.50 mm |
| Paste aperture array | 2 × 2, 1.35 mm squares, 1.70 mm pitch | 4 × 4, 1.30 mm squares, 1.60 mm pitch |
| Rounded aperture corner ratio | 0.05 | 0.05 |
| Copper mask expansion | 0.025 mm | 0.025 mm |

Land pattern is an engineering design derived from manufacturer package dimensions, not a claimed manufacturer-recommended PCB land pattern. Nominal lead length overlap increases from 0.10 to 0.40 mm. Nominal heel/toe extensions: 0.05 / 0.25 mm. Stencil aperture coverage ~63% / ~64%; final stencil thickness, transfer efficiency, voiding and filled/capped via-in-pad process require assembly qualification.

Sources: AXP2101 datasheet V1.0 p59 figure8-1; V851S/V851SE datasheet V0.1 merged PDF p36 (printed p22) figure2-1; TI SLUA271C (2023-12) §3.3,3.4,4.4.

Scripts use the existing project geometry router. Native KiCad DRC is the acceptance check; geometry routing alone is not sufficient. Critical nets stay on F.Cu without added vias. In1 remains the ground plane. Differential length/impedance/return-path qualification is an existing open issue.

## Notes kept from discarded `grok-test` (do not merge that PCB)

`grok-test` enlarged U2 EPAD to 6.5 mm on the pre-closeout board (`14fc664`) and never reached DRC 0. Its copper is obsolete; these corridor constraints are the only part worth keeping. Vias stay 0.60/0.30 mm.

- 1V8 U2-37: PMIC_SDA F.Cu vertical at x≈16.34 blocks south escape. Rip that SDA stub only; keep SCL on F.Cu if possible. Target via ~(16.55, 21.50), then In2 west around y≈20.4 / x≈11.5 to island via `(9.685, 26.500)`, avoiding the SD_PWR_EN In2 ridge.
- DRAM via `(17.125, 22.300)` is tight to 1V8; keep DRAM F.Cu at x≥17.55. Move C21 south only `(16.925, 20.55)→(16.925, 20.20)`; a large east move hits I2C0_SDA/RTC vias.
- D10 at `(24.1, 28.0)` blocks U2 east escape. Nudge, DRC immediately; then SD_CMD south dogbone. Aggressive D10 moves shorted SD_D0 against SD_D1/J5.
- Closing 1V8 while shorts were still open was tried and reverted. Keep shorting_items at 0 before taking more nets.
