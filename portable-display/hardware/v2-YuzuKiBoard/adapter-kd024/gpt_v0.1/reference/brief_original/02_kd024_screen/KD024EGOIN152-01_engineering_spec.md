# KD024EGOIN152-01 Engineering Specification

Source: `KD024EGOIN152-01 SPEC V1.pdf`  
Module: KD024EGOIN152-01  
Panel: 2.4-inch Rigid AMOLED  
Driver IC: RM690B0  
Resolution: 450 x 600 RGB  
Document version: Ver.02  
Document date: 2026-08-26

> This file is a structured engineering transcription/summary of the supplied display specification for PCB, firmware, and project integration work. It does not add undocumented electrical behavior.

## 1. Quick suitability summary

- Display type: Rigid AMOLED
- Size: 2.4 inch
- Resolution: 450 x 600
- Color depth: 16.7M / 24-bit
- Frame rate: 60 Hz
- Interface: MCU / MIPI
- MIPI mode: supported
- MCU mode: supported
- Command mode: supported
- Video mode: supported
- AOD (Always On Display): supported
- AOD RTC: not supported
- Brightness dimming: supported
- Gamma correction: supported
- Driver IC: RM690B0
- Driver RAM: 1/3 RAM
- Touch: not specified / no touch interface in this module specification

## 2. Mechanical

| Item | Value |
|---|---|
| Active area | 36.72 x 48.96 mm |
| Panel outline | 38.72 x 51.56 mm |
| Pixel size | 81.6 x 81.6 um |
| Pixel pitch | 81.6 um |
| Pixel density | 311 PPI |
| Pixel aspect ratio | 3:4 |
| Panel thickness | 0.5 mm |
| Polarizer thickness | 0.147 mm |
| SCF thickness | 0.13 mm |
| Bonding type | COF |
| TFT technology | LTPS |
| Matching connector | Molex 502598-4591 |
| FPC pins | 45 |
| Shipping state | FPC shipped unfolded |

## 3. Optical

Test condition in the source document: VCI=3.3V, VDDIO=1.8V, ELVDD=3.6V, ELVSS=-3.6V, Ta=25C.

| Item | Typical / Requirement |
|---|---|
| Brightness | 800 cd/m2 typical (720 min, 880 max) |
| Contrast ratio | 1,000,000:1 listed |
| Viewing angle | 80 deg min in L/R/U/D at Cr>=10 |
| Response time | 2 ms typical |
| Gamma | 2.2 typical (2.0 to 2.4) |
| Color temperature | 7500 K typical |
| DCI-P3 ratio | 100% typical, 97% min |
| Front polarizer direction | 135 deg |
| Operating temperature | -20 to +80 C |
| Storage temperature | -40 to +80 C |

### Lifetime note

The supplied source contains inconsistent lifetime values:

- One table lists OLED lifetime LT95 as 30000 hours at 25C.
- Section 3.10 states LT95 > 290 h under its stated test method.

Do not reconcile these values without vendor confirmation.

## 4. Electrical supplies

### 4.1 DC characteristics

| Rail / Signal | Symbol | Min | Typ | Max | Unit |
|---|---:|---:|---:|---:|---|
| Analog power supply | VCI | 2.7 | 3.3 | 3.6 | V |
| I/O supply | VDDIO | 1.65 | 1.8 | 3.3 | V |
| OLED positive input | ELVDD | 2.0 | 3.6 | 6.0 | V |
| OLED negative input | ELVSS | -4.7 | -3.6 | -0.4 | V |
| Input high | VIH | 0.8*VDDI | - | VDDI | V |
| Input low | VIL | 0 | - | 0.2*VDDI | V |
| Output high | VOH | 0.8*VDDI | - | VDDI | V |
| Output low | VOL | 0 | - | 0.2*VDDI | V |
| Frame frequency | frame | - | 60 | - | Hz |

### 4.2 Normal display power consumption

Conditions: VDDIO=1.8V, VCI=3.3V, ELVDD=3.6V, ELVSS=-3.6V, 100% pixels on, 60 Hz.

| Item | Typical | Max |
|---|---:|---:|
| VCI current | 3.1 mA | 3.6 mA |
| VCI power | 10.23 mW | 11.88 mW |
| VDDIO current | 1.3 mA | 1.5 mA |
| VDDIO power | 2.34 mW | 2.7 mW |
| ELVDD current | 67.1 mA | 73 mA |
| ELVSS current | 67.0 mA | 72.4 mA |
| Panel power | 483 mW | 526 mW |

AOD power consumption is not specified in the supplied document.

## 5. Interface selection

Interface mode is selected by IM1 / IM0:

| IM1 | IM0 | Interface |
|---:|---:|---|
| 0 | 0 | MIPI |
| 1 | 1 | MCU |

Other combinations are not defined in the supplied document.

## 6. 45-pin FPC pinout

| Pin | Symbol | Direction | Function |
|---:|---|---|---|
| 1 | GND | Power | Ground |
| 2 | GND | Power | Ground |
| 3 | ELVSS | Power | Negative power supply for panel |
| 4 | ELVSS | Power | Negative power supply for panel |
| 5 | GND | Power | Ground |
| 6 | ELVDD | Power | Positive power supply for panel |
| 7 | ELVDD | Power | Positive power supply for panel |
| 8 | GND | Power | Ground |
| 9 | VCI | Power | Power supply for display driver IC analog system |
| 10 | GND | Power | Ground |
| 11 | VDDIO | Power | Power supply for display driver IC interface and logic system |
| 12 | GND | Power | Ground |
| 13 | TE1 | O | IC status active reporting pin |
| 14 | SWIRE | O | SWIRE protocol setting pin of Power IC |
| 15 | TE | O | Tearing effect output pin; enabled by software command; otherwise low |
| 16 | RESX | I | Display driver reset, active low |
| 17 | GND | Power | Ground |
| 18 | SDI_RDX | I/O | RDX read strobe in 80-series MPU interface |
| 19 | DCX | I | Display data / command selection in 80-series MPU interface |
| 20 | SCL | I | WRX write strobe in 80-series MPU interface |
| 21 | CSX | I | Chip select, active low, in 80-series MPU interface |
| 22 | D0 | I/O | 8-bit bidirectional data bus for 80-series MPU interface / input for RGB I/F |
| 23 | D1 | I/O | Data bus |
| 24 | D2 | I/O | Data bus |
| 25 | D3 | I/O | Data bus |
| 26 | D4 | I/O | Data bus |
| 27 | D5 | I/O | Data bus |
| 28 | D6 | I/O | Data bus |
| 29 | D7 | I/O | Data bus |
| 30 | GND | Power | Ground |
| 31 | IM1 | I | Interface mode select |
| 32 | IM0 | I | Interface mode select |
| 33 | GND | Power | Ground |
| 34 | GND | Power | Ground |
| 35 | D0P | I/O | MIPI differential data positive |
| 36 | D0N | I/O | MIPI differential data negative |
| 37 | GND | Power | Ground |
| 38 | GND | Power | Ground |
| 39 | CLKP | I | MIPI differential clock positive |
| 40 | CLKN | I | MIPI differential clock negative |
| 41 | GND | Power | Ground |
| 42 | GND | Power | Ground |
| 43 | MTP | Power | MTP programming supply; leave open or connect to GND in normal condition |
| 44 | GND | Power | Ground |
| 45 | GND | Power | Ground |

## 7. MIPI interface parameters

The module uses one MIPI data lane plus one clock lane:

- Data lane: D0P / D0N
- Clock lane: CLKP / CLKN
- MIPI speed: 456 MHz
- DCLK: 18.5 MHz
- Frame rate: 60 Hz

Porch settings supplied for MIPI initialization:

- VBP = 6
- VFP = 4
- VSW = 2
- HBP = 24
- HFP = 24
- HSP = 4

## 8. Power-on initialization code

### 8.1 MIPI

```text
0xFE 0x00;
0x2A 0x00 0x10 0x01 0xD1;
0x2B 0x00 0x00 0x02 0x57;
0x35 0x00;
0x51 0xFF;
0x30 0x00 0x01 0x02 0x56;
0x12 0x00;
0x11;
wait 120ms;
0x29;
```

### 8.2 MCU

```text
0xFE 0x20;
0x26 0x0A;
0x24 0x80;
0xFE 0x00;
0x2A 0x00 0x10 0x01 0xD1;
0x2B 0x00 0x00 0x02 0x57;
0x35 0x00;
0x51 0xFF;
0x30 0x00 0x01 0x02 0x56;
0x12 0x00;
0x11;
wait 120ms;
0x29;
```

### 8.3 Power-off

```text
0x28;
0x10;
wait 5 Frames; // 83ms @ 60Hz
mipi low;
reset pull low;
```

### 8.4 Idle mode

Enter:

```text
0xFE 0x00;
0x39;
```

Exit:

```text
0xFE 0x00;
0x51 0xFF;
wait 50ms;
0x38;
```

### 8.5 HBM mode

Enter:

```text
0xFE 0x00;
0x66 0x02;
```

Exit:

```text
0xFE 0x00;
0x66 0x00;
```

## 9. AOD information present in the source

The module specification explicitly states:

- AOD (Always On Display): Y
- AOD RTC: N

The supplied document does NOT provide:

- AOD entry command sequence
- AOD exit command sequence
- AOD refresh rate
- AOD power consumption
- Maximum AOD region
- Whether MIPI clock/data can stop while AOD is maintained
- Detailed internal RAM behavior for AOD
- AOD-specific RM690B0 register/application note

These items require vendor confirmation before relying on a particular low-power architecture.

## 10. PCB integration notes derived directly from the document

### Hardware facts that can be used now

- 45-pin FPC
- Recommended connector: Molex 502598-4591
- MIPI uses D0P/D0N + CLKP/CLKN
- Reset pin RESX is active low
- TE and TE1 are output/status-related signals
- IM1/IM0 select interface mode
- VCI, VDDIO, ELVDD and ELVSS are separate supplies
- ELVSS requires a negative rail
- MTP should be left open or tied to GND in normal use

### Missing vendor reference information

The revision history states that the schematic was removed in Rev.02. The remaining “Schematic Circuit Diagram” is only a block diagram and does not specify the recommended DC-DC / AMOLED bias implementation.

Vendor information still desirable before finalizing the power section:

1. Recommended ELVDD / ELVSS power IC
2. Reference circuit and passive values
3. SWIRE connection and programming behavior
4. Power-on/off timing details in an unambiguous tabular form
5. AOD application note / register sequence

## 11. Reliability conditions

| Test | Condition |
|---|---|
| Thermal humidity operating | +60C, 90% RH, 240 h |
| Low temperature operating | -20C, 240 h |
| High temperature operating | +80C, 240 h |
| High temperature storage | +80C, 240 h |
| Low temperature storage | -40C, 240 h |
| Thermal cycle storage | -40C to +80C, 1 h/cycle, 100 cycles |

## 12. Source document revision history

| Rev | Description | Date |
|---|---|---|
| 01 | Initial Issue | 2025-12-16 |
| 02 | P16 Remove the schematic | 2026-08-26 |

## 13. Recommended use of this file

This Markdown file is intended to be the project’s working screen specification for:

- schematic capture
- PCB connector/pin mapping
- power-tree planning
- V851s MIPI integration
- firmware initialization
- issue tracking with the display vendor
- future AI-assisted design/review

When vendor provides new information, append it under a dated “Vendor Addendum” section rather than silently overwriting unsupported assumptions.
