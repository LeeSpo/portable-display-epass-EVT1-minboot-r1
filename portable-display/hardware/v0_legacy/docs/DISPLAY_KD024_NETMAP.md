# KD024EGOIN152-01 host netmap — current candidate

RM690B0, MIPI DSI one lane; IM1/IM0 strapped to ground. J4 is the revised
`Sameat:FPC45` for candidate Molex 502598-4593; module reference -4591 compatibility
remains to be checked. `fabrication_released` remains false.

| J4 pins | Host net / destination |
|---|---|
| 3, 4 | ELVSS, U10 OUTN |
| 6, 7 | ELVDD, U10 OUTP / FBS |
| 9 | LCD_3V3, U8 VOUT |
| 11 | LCD_1V8, R29 from 1V8 |
| 13 TE1 | Explicit NC |
| 14 SWIRE | LCD_SWIRE to R31 pad 1; R31 DNP |
| 15 TE | LCD_TE, U2 pin 3 (PD20) |
| 16 RESX | LCD_RST, U2 pin 2 (PD19) |
| 35 / 36 | DSI_D0P / DSI_D0N, U2 pins 81 / 80 |
| 39 / 40 | DSI_CKP / DSI_CKN, U2 pins 85 / 84 |
| MP1 / MP2 | GND |

LCD_EN comes from U2 pin 4 and controls both U8 and U10. Unused U2 DSI lane-1
pins 82/83 and J4 TE1 are explicit NC, rather than orphan global labels.
J4 parallel-interface pins 18–29 are NC. Exact remaining pin assignments are in
`design/pin_contract.json`; that file records intent, not manufacturer signoff.

The TFT backlight components U7/L4/D4/R19/C27/C28 are removed from this AMOLED
variant in the schematic, board, library and generator. AMOLED brightness is
controlled in firmware; no LEDA/LEDK backlight is fitted.

See [current PCB validation](DISPLAY_PCB_STATUS.md),
[power/control restrictions](DISPLAY_EL_TPS65631.md), and
[connector/package review](DISPLAY_FOOTPRINT_REVIEW.md). AOD and physical display
operation have not been demonstrated.
