# 预投板阻塞项修复：决策日志（fix/preflight-blockers）

> 用户把所有选择都交给了我们，原则是：**先保证能工作，再尽量便宜**。优先选 JLC/LCSC 有库存的料，basic 库优先。
> DRC 规则一律不放宽，也不加任何豁免。过孔统一 0.60/0.30。U1/U2 不移动。fabrication 仍为 **未放行**。
> 价格和库存是 2026-10-15 查询 JLC/LCSC API 得到的。

## 1. FEL 铜皮 + 原理图同步
- 详见 `FEL_REPAIR_CN.md`。原理图由 `tools/build_candidate_schematic.py` 从 PCB 重新生成。parity 0 / ERC 0。

## 2. LCD_EN 默认关断：R35 10k（C25744，basic，约 $0.0005）
- 评审建议在 R31 上贴 100k。核对后发现 **R31 不是下拉**，它是 LCD_SWIRE↔LCD_EN 之间的 0R 跨接，应保持 DNP。如果把它贴上，SWIRE 和 EN 会被短接，所以没有采纳这条建议。
- 因此新增 R35 下拉到 GND。阻值取 10k 而不是 100k：按 GPIO 漏电最坏 10 µA 估算，10k 上的压降 ≤0.1 V，可以可靠地保持 U8 / U10 CTRL 为低；换成 100k 最坏会到 1 V，不安全。PD21 驱动为高时，10k 上的电流是 0.33 mA，可以接受。

## 3. D6–D14 ESD：ESDLC5V0LB（扬杰，C20168172，$0.0297 @20+，库存约 2900）
- 5 V 双向，约 3 pF，适合 SD 和按键这类低速信号。原来的料与封装不一致。新建 `sameat.pretty/DFN1006-2`，焊盘按数据手册 p5 绘制（±0.425，0.55×0.60）。

## 4. J2 电池座：Megastar ZX-SH1.0-3PWT（C7430445，$0.0573，库存约 67k）
- J1 和 H4 之间只有 8.49 mm。PH2.0（11.7 mm）和 MX1.25（9.4 mm）都放不下，JST S3B-PH（C265101）也缺货。SH1.0 3P 卧式能放下。
- **注意 1**：每个触点额定 1 A。1S 锂电只要平均电流 <1 A 就可以用，峰值应该由 PMIC 限流。
- **注意 2**：电池线序是 1=VBAT、2=NTC、3=GND。市售 SH1.0 电池的线序**不统一**，接电前必须用万用表核对。
- 新封装 `SH1.0_3P_RA` 按厂家图纸绘制。VBAT/NTC/VBUS/PMIC_IRQ 已重新布线，并补了一条 In2 3V3 桥接，让 3V3 带状铺铜保持连续。

## 5. J5 microSD —— **未完成（开放项）**
- 原料 MUP-M617-2（C5205359）在 JLC 缺货。选定的替代是 **XKTF-0803-0（XKB，C381083，$0.2058，库存约 1613，push-push，11.25×6 mm）**，可以放进原来的位置。
- 封装 `sameat.pretty/XKTF-0803-0.kicad_mod` 已提交。焊盘与 JLC EasyEDA 官方封装和 XKB 图纸逐一核对过。
- 没有换上板的原因：换件后引脚顺序会整体反过来。原来的 SD 走线、以及 RTC_3V3 / PMIC_SDA / PWRON_N 的长线都需要重新布线。我们写的自动布线器做不到 0 违规（freerouting 2.1 也会卡在 11–18 根未布通）。为了不让分支变脏，**PCB 目前仍然是旧的 J5（BOM 里那个料缺货）**。
- 建议：在 KiCad GUI 里用交互式推挤布线完成，大约 1–2 小时。SD 走线放在 F/B 层，不要走 In2。可以顺便把 Y1 下方的 SD 线移开（见第 9 节）。

## 6. U8 输入电容（评审 g）
- C53 1 µF（CL05A105KA5NQNC，C52923，basic，$0.0079）+ C54 100 nF（CL05B104KO5NNNC，C1525，basic）。两颗都在顶层，距离 U8.1 焊盘边 ≤0.65 mm。GND 过孔放在焊盘外，焊盘边到孔的距离 ≥0.15 mm。

## 7. VBUS 线宽（评审 h）
- J1→C32/U1.37 主路径上，B.Cu 的两段 0.25 mm 已加宽到 0.6 mm。
- J1 附近 F.Cu 的 0.25 mm 瓶颈没有加宽：加宽到 0.6 会碰到 CC2、SBU1 焊盘和 C2 的 GND，DRC 不过。J1 A4/B9 一侧另有一条 0.6 mm 并联路径。
- U1.37 的扇出保持 0.18 mm，这是焊盘间距限制的。
- 剩下的 0.127 mm 段在 U9 那条小电流支路上。

## 8. U2 去耦（评审 f）—— **未完成（开放项）**
- 我们对 U2 的 44/47/55（3V3）、37（1V8）、13/17/75（CORE）做了自动搜索：要求顶层 0402、距焊盘 ≤2 mm、GND 过孔在焊盘外，结果**都找不到合规位置**。U2 周围的扇出和其它 courtyard 已经占满，也不能改 U2 或它的 courtyard。底层附近又没有对应电源网络的铜皮可以接。
- 现状：最近的去耦电容离引脚 5.7–11 mm，但这些电源在 In2 都有平面，In1 是 GND，所以电源回路阻抗本身不算差。
- 建议：在 GUI 里重新整理 U2 扇出，为顶层电容腾出位置。另一条路是放到底层，直接贴在 U2 背面，但这样就变成**双面 SMT**，JLC 要多收一次底面贴装的工程费和钢网费，成本明显上升。因为用户要求便宜，我们没有自动这样做。

## 9. 其它评审项
- (b) PMIC_SCL：B.Cu 上一段走线从 L2/LX_CORE 投影下方穿过。核实后，中间的 In1 在该处是**完整的 GND 铺铜**（已用 pcbnew 采样点确认），F 层到 B 层的耦合被屏蔽；I2C 只有 100/400 kHz。**决定不改线**，避免引入新的违规。
- (c) Y1：In1 和 In2 在 Y1 正下方都是 GND。B.Cu 上有 SD_D0、SD_D2、SD_DET、SD_PWR_EN、SOC_LDO_1V8 从下方穿过，它们被 In1 GND 隔开。In2 上有 SD_DET、SD_PWR_EN 两段静态信号从边缘经过。XIN 5.4 mm、XOUT 7.4 mm，受限于 U2 不能动。**留到 J5 返工时一起把 SD 线移出 Y1 区域**。
- (d) MIPI DSI：D0 skew 11.05 mm、CK 5.00 mm，CKP 有一个 90° 拐角。J4 和屏幕都还没定，**本轮不改**，等 J4 定型后再做等长和 45° 拐角。
- (e) I2C0 上拉 R15/R16：**保持接在主 3V3**。
  - 3V3 关断时，总线被拉到约 0 V。U4（LIS2DW12）和 U5（RV-3028）由 RTC_3V3 供电，它们的 IO 处于低电平，这在允许范围内，不会倒灌。
  - 如果把上拉改到 RTC_3V3，3V3 关断时总线仍是 3.3 V，电流会通过 V851S 的 IO 钳位二极管倒灌进未上电的 SoC（10k 约 0.33 mA）。这种情况更糟。
  - 代价：SoC 关机时无法访问 I2C。这没有关系，唤醒走 INT 线（缓冲器 U11 支持 Ioff）。

## 10. P1 项（只记录，不编造测量值）
- RTCLDO 精度 ±10%（PMIC C3036461），而 LIS2DW12 绝对最大值是 3.6 V。如果出厂设定是 3.3 V，+10% = 3.63 V，会略超绝对最大值。**需要实测 RTC_3V3**，或者确认 OTP 设定值。
- VSYS 与 TPS65631（U10）的输入范围 2.9–4.5 V：电池电压 4.2 V 在范围内，但 VBUS 直通或充电时 VSYS 的上限必须由 PMIC 设定值保证。**需要实测**。
- PMIC OTP：C3036461 的出厂电压、使能和时序配置，在现有资料里没有说明（`check_power_contract` 的 remaining_blocker）。

## 验证（verification/preflight_fix_20261015）
- DRC（含 --schematic-parity --refill-zones --severity-all）：0 violations / 0 unconnected / 0 parity。
- ERC：0。
- check_power_contract / check_fel_recovery / check_usb_routing / check_wake_domain：static_checks_passed = true。
