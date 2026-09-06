# EL bias: TPS65631DPDR

**Pick for EVT1:** TI `TPS65631DPDR` · LCSC **C165127** · WSON-12-EP 3×3  
Datasheet: https://www.ti.com/lit/ds/symlink/tps65631.pdf

## Why this part

| Need | TPS65631 |
|---|---|
| ELVDD + ELVSS | Yes (VPOS / VNEG) |
| ~70 mA panel | Up to ~250–300 mA |
| LiPo / VSYS | VIN 2.9–**4.5** V |
| SWIRE-class control | CTRL one-wire (enable + VNEG program) |
| JLCPCB / hand rework | WSON-12, LCSC in stock |
| Extra AVDD rail | Not required (KD024 VCI is separate) |

Runners-up: `TPS65632` (adds unused AVDD), `SGM3839` (WLCSP-49, harder), `MP5611` (TQFN, less LCSC clarity).

## Defaults vs panel typ

| Rail | Panel typ (optical) | Panel abs | U10 default |
|---|---:|---:|---:|
| ELVDD | 3.6 V | 2.0–6.0 | **4.6 V** fixed |
| ELVSS | −3.6 V | −4.7–−0.4 | **−4.0 V** (CTRL can set −3.6 = 9 pulses) |

4.6 / −4.0 is inside the module absolute range. Optical typ ±3.6 is a test condition, not a hard host requirement.

## Host wiring (this branch)

- `AVIN`/`PVIN` ← `VSYS` (keep ≤4.5 V)
- `OUTP`/`FBS` → `ELVDD` → J4
- `OUTN` → `ELVSS` → J4
- `CTRL` ← `LCD_EN` (same enable as VCI load-switch U8)
- Panel `SWIRE` (`LCD_SWIRE`) **open by default** (RM690B0: unused → open)
- `R31` 0Ω **DNP**: populate only if joining panel SWIRE to CTRL for VNEG programming (needs open-drain-friendly drive)
- Passives per TI typical: 2×4.7 µH, VIN 2×10 µF, ELVDD 10 µF, ELVSS 2×10 µF, CT 100 nF

## Bring-up note

1. Assert `LCD_EN` → U8 VCI + U10 EL± start (ELVSS ~10 ms after CTRL high).
2. Then release `LCD_RST` / start MIPI.
3. Optional: program VNEG to −3.6 V via CTRL pulses (or R31+panel SWIRE once validated).
