# Portable Display V1.0-EVT1 hardware notes

This is a reference-derived engineering validation design. The display island (MIPI DSI, FPC, backlight) is frozen pending an OLED panel lock; those nets are intentionally unrouted. Non-display power, USB, storage, keys and wake path are the active work. It has not been physically built or electrically validated.

## Architecture

- V851s boots Tina Linux on the Cortex-A7 and loads the E907 RTOS image. The E907 manages connected standby; the A7 resumes for display updates and H.264 playback.
- AXP2101 provides USB/battery power path, charging, rail sequencing and fuel-gauge data. The intended defaults are DCDC1=3.3 V, DCDC3=0.93 V, DCDC4=1.5 V and ALDO1=1.8 V. Confirm the ordered AXP2101 OTP/default configuration with the supplier before assembly.
- RV-3028-C7 and LIS2DW12 remain on `RTC_3V3`. Their active-low interrupts create an approximately 80 ms PWRON pulse through SN74LVC1G123 so a latched alarm cannot look like a long power-key press.

## Locked pin allocation

| Function | V851s pins |
|---|---|
| MIPI DSI | PD1 D0N, PD2 D0P, PD3 D1N, PD4 D1P, PD5 CKN, PD6 CKP |
| Display control | PD19 RESET, PD20 PWM, PD21 power enable |
| MicroSD (only onboard boot media) | PF0-PF5 data/clock/command, PF6 detect, PH12 power control |
| Boot straps / FEL | PC2 BOOT0 (R10 pull-up, SW6 to GND), PC3 BOOT1 (R28 pull-up); PC0/PC1/PC4/PC5 NC. SPI NAND island removed. |
| Sensors | PE4 TWI0 SCL, PE5 TWI0 SDA, PE6 accelerometer IRQ, PE7 RTC IRQ |
| PMIC | PH13 SCL, PH14 SDA, PE2 IRQ |
| Debug | PH9/PH10 A7 UART0; PE0/PE1 E907 UART3 |
| Buttons | GPADC0 ladder; power key to AXP2101 PWRON |

## Display connector

`TFT-H035B22WVIST8N20_V3-0`, 20-pin 0.5 mm bottom-contact FPC:

| Pin | Signal | Pin | Signal |
|---:|---|---:|---|
| 1-5 | NC (touch option) | 6 | LCD_3V3 / VCI |
| 7 | LCD_3V3 / IOVCC | 8 | GND |
| 9 | DSI_D1P | 10 | DSI_D1N |
| 11 | GND | 12 | DSI_CKP |
| 13 | DSI_CKN | 14 | GND |
| 15 | DSI_D0P | 16 | DSI_D0N |
| 17 | GND | 18 | LCD_RST |
| 19 | LEDK | 20 | LEDA |

Timing: 480x800, HPW 10, HBP 48, HFP 48, VPW 10, VBP 20, VFP 20, nominal pixel clock 30 MHz. Copy the complete ST7701S initialization and sleep sequences from the purchased panel revision's datasheet into firmware; do not assume another ST7701S panel uses the same sequence.

## Mechanical and fabrication

- PCB: 58x110 mm, 1.0 mm, four layers. L1 components/signals, L2 solid ground, L3 power/slow signals, L4 signals.
- Nominal enclosure allowance: 62x114x15 mm. Rear battery envelope: maximum 50x80x6 mm.
- USB and MIPI are specified as 90-ohm differential networks. Recalculate physical trace geometry using the exact JLCPCB stackup selected at order time; do not substitute the nominal drawing values without an impedance coupon/order review.
- Through vias for QFN fanout are 0.40 mm / 0.20 mm drill (order JLCPCB with 0.20 mm via hole). The SoC-to-FPC rectangle is a drawing-layer keepout for a later OLED MIPI bundle.
- Display nets (DSI_*, LCD_*, LEDA/LEDK, BL_SW) are frozen. Do not treat unconnected display items as a reason to delay non-display bring-up.
- Screen and battery samples must be measured before mechanical freeze.
- Board origin is the bottom-left corner of Edge.Cuts (0, 0) in millimetres. CPL Mid X/Y uses that origin on the top side.

## Important limitations

- No firmware, enclosure, radio, audio, touch or always-on display is included.
- A generic AXP2101 may not contain the V851s rail defaults. Supplier confirmation is a fabrication gate.
- Stock levels and CPL rotations must be rechecked in the JLCPCB ordering preview.
- Do not order a display-capable PCBA until an OLED (or the current IPS) is locked and those nets are routed. A power/USB/storage spin is only useful if you accept no panel.
