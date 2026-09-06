# KD024EGOIN152-01 host netmap (EVT1)

Module locked for wiring on `feat/display-2p4-aod-rm690b0`.  
Connector: Molex **502598-4591** (45-pin, footprint `Sameat:FPC45` as J4).  
Driver: **RM690B0**. Interface: **MIPI 1-lane** (`IM1=0`, `IM0=0` strapped to GND).

`fabrication_released` remains **false**. EL± PMIC is **not** chosen — nets only.

## Power

| Module | Host net | Source |
|---|---|---|
| VCI | `LCD_3V3` | `3V3` via U8 (`LCD_EN`) |
| VDDIO | `LCD_1V8` | `1V8` via R29 0Ω |
| ELVDD | `ELVDD` | U10 TPS65631 `OUTP` (default 4.6 V) |
| ELVSS | `ELVSS` | U10 TPS65631 `OUTN` (default −4.0 V) |
| SWIRE | `LCD_SWIRE` | Open default; optional `R31`→`LCD_EN`/CTRL |

## Control / MIPI

| Module | Host net | SoC |
|---|---|---|
| RESX | `LCD_RST` | U2 PD19 |
| TE | `LCD_TE` | U2 PD20 (was `LCD_PWM`) |
| TE1 | `LCD_TE1` | unrouted GPIO TBD / NC OK for first bring-up |
| D0P/D0N | `DSI_D0P`/`DSI_D0N` | U2 PD2/PD1 |
| CLKP/CLKN | `DSI_CKP`/`DSI_CKN` | U2 PD6/PD5 |

Host `DSI_D1P`/`DSI_D1N` stay on SoC but **do not** land on J4 (1-lane module).

## Explicit NC

Pins 18–29 (MCU/RGB bus), brightness via register `0x51` (no LEDA/LEDK).  
U7 TPS61169 backlight chain is **DNP**.

## Open gates

1. PCB: place U10 + inductors, replace FPC20 island with FPC45, route MIPI 1-lane + EL±.
2. Confirm VSYS never exceeds TPS65631 VIN max 4.5 V under charge.
3. AOD command sequence / power policy (firmware).
4. KiCad ERC/DRC after PCB edit.

See also `docs/DISPLAY_EL_TPS65631.md`.
