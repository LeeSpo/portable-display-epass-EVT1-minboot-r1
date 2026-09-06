# 电气问题清单与本布局稿修正

**适用对象：上传板的原始网络，以及本 38×64 mm 布局候选上已经改过的焊盘网络。**

本报告区分三个层次：①从 PCB 直接读到的网络事实；②制造商资料中的引脚与应用信息；③仍需原理图、屏厂或实物确认的判断。本目录没有原理图，本次修正只改 PCB 焊盘网络和 U6 定时 RC 的位置，不是完整 ERC。

`source_pad_net_map.json` 现为**修正后**的黄金映射，与当前 PCB 一致。

## A. U6：SN74LVC1G123 脚序 — 本布局稿已改

原板把符号脚号当成封装脚号，TI DCT/DCU 实际定义见资料 [1] 第 3 页。本版已按封装脚改接，并把 R12/C23 移到 6/7 脚一侧。

| 物理脚号 | TI 定义 | 原板网络 | 本布局稿网络 |
|---:|---|---|---|
| 1 | /A，下降沿触发输入 | WAKE_PULSE | WAKE_REQ_N |
| 2 | B，上升沿触发输入 | GND | RTC_3V3（拉高，只用 /A） |
| 3 | /CLR，低有效清除 | WAKE_CEXT | RTC_3V3 |
| 4 | GND | WAKE_REXT | GND |
| 5 | Q，输出 | WAKE_REQ_N | WAKE_PULSE |
| 6 | Cext | RTC_3V3 | WAKE_CEXT |
| 7 | Rext/Cext | RTC_3V3 | WAKE_REXT |
| 8 | VCC | RTC_3V3 | RTC_3V3 |

R12=820k、C23=100n 仍给出约 80 ms 脉宽，拓扑未改。R12 现为 (31.0, 8.0)，C23 为 (31.0, 9.3)。上电前仍应核对该脉宽是否满足 AXP2101 PWRON 的实际按键时间。

## B. U1：AXP2101 的 VMID — 本布局稿已改

原板：U1-34、U1-36 与 C38-1 都在 `VSYS`。

资料 [2]：脚 34 为 VSYS，脚 36 为 VMID 输出，参考电路单独接去耦。本版：

- 新增网络 `VMID`
- U1-36、C38-1 → `VMID`；C38-2 仍为 GND
- U1-34 及 SYS 储能电容仍为 `VSYS`

C1/C2 靠近 U1 底侧，C3 靠近 BAT，C11 靠近 VREF，C40/C41 靠近 VIN，这些是布局位置，不是取值审签。电感、电容有效容量与 PMIC 默认输出仍需审核。

## C. U2：1.8 V 输入与内部 LDO — 本布局稿已按脚位表拆开

原板把 U2-14/37/62/79 和 C34/C37 全部放在 `SOC_LDO_1V8`，与 PMIC 的 `1V8` 不相连；`SOC_AVCC` 只有 U2-48 和 C35。

依据用户提供的 V851S 脚位表 [7]：

| 脚 | 脚位表名称 | 判定 | 本布局稿网络 |
|---:|---|---|---|
| 14 | VCC-LDOA&PLL（VCC-LDOA **OUT** & PLL Power） | 内部 LDO 输出 | `SOC_LDO_1V8`（U2-14、C34、C37） |
| 37 | VDD18-DRAM | 1.8 V 输入 | `1V8` |
| 62 | VCC-PA&VCC-MCSI | GPIOA/CSI 电源输入 | `1V8`（摄像头未用） |
| 79 | VCC-MDSI | MIPI DSI PHY 电源输入 | `1V8`（1-lane 先按 1.8 V；若手册要求 3.3 V 只改此脚） |
| 48 | AVCC | 模拟电源；不并到 3.3 V | `SOC_AVCC`（U2-48、C35） |

不要把脚 14 的 LDOA 输出再短到 `1V8`。AVCC 若后来证实必须外供，再加 0 Ω 选择，本轮不加。

## D. 显示：SWIRE 与 LCD_EN — 保持隔离

屏座第 14 脚 `SWIRE` 为输出。网络仍为：

`J4-14 LCD_SWIRE → R31（0 Ω，**DNP**）→ LCD_EN`

`LCD_EN` 连接 U2-4、U8-3（TPS22918 ON）、U10-7（TPS65631 CTRL）。R31 不贴装时 SWIRE 与主机使能在电气上断开。不要在 `LCD_EN` 上发 TPS65631 编程脉冲，那会同时开关 VCI。

屏幕本次布局只保留一条数据差分对与一条时钟差分对；IM0/IM1 接地选择 MIPI，MTP 接地。尚未完成上电时序或初始化验证。

## E. TPS65631：电压与屏厂推荐工作点仍需确认

资料 [4] 给出 TPS65631 正输出固定约 +4.6 V，负输出默认约 -4.0 V。屏幕资料典型测试条件为 +3.6 / -3.6 V。绝对最大范围不能代替工作点签核。本轮不改该电路。

U10 输入接到 VSYS；TPS65631 输入范围为 2.9～4.5 V，VSYS 全工况范围尚未验证。

## F. 其他未签核事项

显示 VDDIO 当前使用 `LCD_1V8`，主控相关 I/O 与 RESX/TE/SWIRE 的电平兼容性需逐脚审核。

RTC/姿态传感器等常供电器件与主控可关断电源之间，需要审核 I²C 上拉归属、断电漏电、倒灌、复位和唤醒极性。

QFN、屏座、USB、microSD 等封装沿用上传板的嵌入几何，未与厂家焊盘图和 3D 包络逐一签核。

没有原理图，本报告不替代完整 ERC、电源时序、PMIC OTP 默认值和充电安全审查。

## 资料与复核来源

[1] Texas Instruments，SN74LVC1G123 数据手册，SCES586E，第 3 页引脚定义。`https://www.ti.com/lit/ds/symlink/sn74lvc1g123.pdf`

[2] X-Powers，AXP2101 Datasheet V1.4，第 8 页引脚表、第 57 页典型应用；通过 LilyGo 提供的制造商资料副本核对。`https://wiki.lilygo.cc/datasheet/AXP2101_Datasheet_V1.4_en.pdf`

[3] 全志开发者社区所提供的 V851S PER2 QFN88 参考原理图，文件名含 AXP2102 V1.2，2022-07-05；不能据此把其中 AXP2102 充电电路直接当作 AXP2101 电路。

[4] Texas Instruments，TPS65631 数据手册，电压参数、引脚图及 Layout Guidelines。`https://www.ti.com/lit/ds/symlink/tps65631.pdf`

[5] 上传的 KD024EGOIN152-01 工程规格、引脚 CSV 和结构化 JSON，原样副本见 `reference/`。

[6] 网络证据：`source_pad_net_map.json`（修正后）与 `geometry_audit.json`。

[7] 全志 `V851S Pinout v0.1`，副本 `reference/v851s_pinout_v0.1.xlsx`。脚 14 标注 VCC-LDOA OUT；脚 37/62/79 为电源输入脚。
