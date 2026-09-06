# Portable Display ePass — V1.0-EVT1

**Product:** Sameat 明日方舟电子通行证 / 挂牌便携显示主机板
**Revision:** V1.0-EVT1 (2026-09-04)
**EDA:** KiCad 9/10
**Status:** Display island frozen. All 54 non-display V851s pins have 0.40/0.20 mm staggered fanout vias. USB/NAND/SD trunks are **not** joined yet. See `manufacturing/evt1/FANOUT_STATUS.md`. **Not physically validated.**

## What this board is

A battery-powered 3.5" MIPI display host:

- Allwinner **V851s** (Cortex-A7 + E907). E907 manages standby; A7 boots, drives MIPI and H.264.
- **AXP2101** USB / single-cell charge / power path / rails / fuel gauge. No TP4056, no MAX17048.
- Panel placeholder **TFT-H035B22WVIST8N20_V3-0** (3.5" IPS) is still in the schematic but **not routed**; V1.0 intends to switch to MIPI OLED before that island is finished.
- **W25N01GV** SPI NAND, MicroSD, LIS2DW12, RV-3028-C7, five side keys.
- No radio, no speaker, no touch, no AOD, no firmware, no enclosure.

## Architecture

```text
USB-C (device, 5.1 kΩ CC, 500 mA default limit)
  │
  ▼
AXP2101 ──── 1S LiPo + 10 kΩ NTC (JST-PH 3-pin)
  ├─ 3.3 V, 1.8 V, 1.5 V, 0.93 V, RTC always-on
  ▼
V851s
 ├── MIPI DSI ── 3.5" 480×800 IPS (FH12-20S)
 ├── TPS61169 backlight (~12 V / 80 mA)
 ├── W25N01GV SPI NAND
 ├── MicroSD (switched 3.3 V)
 ├── LIS2DW12 + RV-3028-C7 on RTC rail
 └── 5 × side keys (GPADC ladder + AXP2101 PWRON)
```

Locked pin map, FPC table, timing and bring-up steps: [docs/HARDWARE.md](docs/HARDWARE.md), [docs/BRINGUP.md](docs/BRINGUP.md).

## Mechanical

- PCB 58 × 110 mm, 1.0 mm, 4 layers: F.Cu / In1 GND / In2 3V3 / B.Cu.
- Rear battery keepout 50 × 80 × 6 mm. USB-C on the bottom edge, MicroSD on the top edge, M2 holes at the four corners.
- Nominal enclosure envelope 62 × 114 × 15 mm.

## How to open and regenerate

1. Install KiCad 9 or 10.
2. Open `portable_display_epass.kicad_pro`.
3. The schematic is four hierarchical sheets. The PCB is `portable_display_epass.kicad_pcb`.

The design is generated from one data file so symbols, footprints and the BOM cannot silently drift:

```bash
python3 tools/generate_evt1.py
./tools/verify_evt1.sh
```

`kicad-cli` is expected at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` or on `PATH`.

## Manufacturing outputs

Written to `manufacturing/evt1/`:

| File | Contents |
|------|----------|
| `portable_display_evt1_bom.csv` | Grouped BOM with LCSC where assigned |
| `portable_display_evt1_cpl.csv` | Top-side centroid (JLCPCB-style) |
| `net_pin_report.csv` | Every pin and net |
| `gerbers/` | Copper, mask, silk, paste, Edge.Cuts (after verify) |
| `erc.json` / `drc.json` | Last ERC/DRC reports |

Re-check LCSC stock, CPL rotation and the JLCPCB 4-layer impedance stackup on the order preview. A generic AXP2101 may not contain V851s OTP defaults.

## Current file-level status

| Check | Result |
|-------|--------|
| Schematic ERC | 0 violations |
| PCB DRC errors / shorts | 0 |
| PCB unconnected | Display nets frozen; other nets maze-routed where possible |
| DRC warnings | Footprint library mismatch, isolated pour islands, silk |
| Schematic–PCB path parity | Extra-footprint warnings; in pcbnew use Update PCB from Schematic if needed |
| Physical EVT | Not built |

Finish in KiCad before fab:

1. Route MIPI (90 Ω), USB 2.0 (90 Ω), MicroSD, SPI NAND, I²C, buttons, backlight.
2. Fan out V851s / AXP2101 with a via class the chosen JLCPCB process allows. 0.35 mm pitch cannot take the project 0.60 / 0.30 mm via on every pin.
3. Refill zones, run DRC, fix unconnected items.
4. Confirm FPC contact side and battery outline against samples.
5. Order 5 boards, not a production run.

First-power sequence: current-limited supply → rails → USB FEL → SPI NAND → MicroSD → panel → wake path. Targets: PMIC-off < 150 µA, E907 standby < 8 mA, backlight ~80 mA. Misses become V1.1; this revision is not production-ready.

## Schematic sheets

| File | Contents |
|------|----------|
| `portable_display_epass.kicad_sch` | Root |
| `01_power.kicad_sch` | USB-C, AXP2101, battery, power key |
| `02_soc_v851s.kicad_sch` | V851s, 24 MHz, SPI NAND, debug |
| `03_sensors.kicad_sch` | LIS2DW12, RV-3028-C7, wake pulse |
| `04_interfaces.kicad_sch` | Panel FPC, backlight, MicroSD, keys |

Local footprints: `sameat.pretty/`.
