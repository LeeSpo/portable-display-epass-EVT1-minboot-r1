# 电源被动件网络对照（自 01_power.kicad_sch）

> 自动/半自动从原理图标签顺序归纳，布线审查时以 KiCad 高亮为准。

## 电感

| 位号 | 值 | 网络 |
|---|---|---|
| L1 | 1 µH / 2 A | `LX_3V3` ↔ `3V3` |
| L2 | 1 µH / 2 A | `LX_CORE` ↔ `CORE_0V93` |
| L3 | 1 µH / 2 A | `LX_DRAM` ↔ `DRAM_1V5` |

## 主要电容（摘录）

| 位号 | 值 | 附近网络 |
|---|---|---|
| C1, C2 | 22 µF | `VSYS`—GND |
| C3 | 1 µF | `VBAT`—GND |
| C4+ | 22 µF 级 | `3V3` / 各 DCDC 输出（见原理图） |
| VREF 旁路 | 1 µF 类 | `VREF`—GND |

采购：DCDC 输出与 VSYS 陶瓷电容选 X5R/X7R，注意直流偏置降额；1 µH 电感选饱和 ≥1.5–2 A（核电/DRAM 峰值）且 DCR 尽量低。

## 原理图扫描原始表

```
R1	5.1k	USB_CC1 — GND
R2	5.1k	USB_CC2 — GND
L1	1uH/2A	LX_3V3 — 3V3
L2	1uH/2A	LX_CORE — CORE_0V93
L3	1uH/2A	LX_DRAM — DRAM_1V5
C1	22u	VSYS — GND
C2	22u	VSYS — GND
C3	1u	VBAT — GND
C4	22u	3V3 — GND
C5	22u	3V3 — GND
C6	22u	CORE_0V93 — GND
C7	22u	CORE_0V93 — GND
C8	22u	DRAM_1V5 — GND
C9	22u	DRAM_1V5 — GND
C10	2.2u	1V8 — GND
C11	1u	VREF — GND
J2	1S LiPo + NTC	VBAT — BAT_NTC
R3	4.7k	3V3 — PMIC_IRQ_N
R4	2.2k	3V3 — PMIC_SCL
R5	2.2k	3V3 — PMIC_SDA
D1	CHARGE	3V3 — CHGLED_A
R6	2.2k	CHGLED_A — CHGLED_N
C32	10u	VBUS — GND
C33	1u	RTC_3V3 — GND
C38	2.2u	VSYS — GND
C39	100n	PMIC_BACKUP — GND
C40	1u	VSYS — GND
C41	1u	VSYS — GND
```
