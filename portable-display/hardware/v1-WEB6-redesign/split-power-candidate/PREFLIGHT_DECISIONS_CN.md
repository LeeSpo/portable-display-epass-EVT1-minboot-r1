# 预投板阻塞项修复：决策日志（fix/preflight-blockers）

> 用户把所有选择都交给了我们，原则是：**先保证能工作，再尽量便宜**。优先选 JLC/LCSC 有库存的料，basic 库优先。
> DRC 规则一律不放宽，也不加任何豁免。过孔统一 0.60/0.30。U1/U2 不移动。fabrication 仍为 **未放行**。
> 价格和库存是 2026-10-15 查询 JLC/LCSC API 得到的。

## 1. FEL 铜皮 + 原理图同步
- 详见 `FEL_REPAIR_CN.md`。原理图由 `tools/build_candidate_schematic.py` 从 PCB 重新生成。parity 0 / ERC 0。

## 2. LCD_EN 默认关断：R35 10k（C25744，basic，LCSC $0.0033 @100）
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
- C53 1 µF（CL05A105KA5NQNC，C52923，basic，$0.0079）+ C54 100 nF（CL05B104KO5NNNC，C1525，basic，LCSC $0.0046 @100）。两颗都在顶层，距离 U8.1 焊盘边 ≤0.65 mm。GND 过孔放在焊盘外，焊盘边到孔的距离 ≥0.15 mm。

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

## J5 microSD 换座与重布线（2026-10-15，已完成）

- **J5 换为 XKTF-0803-0（LCSC C381083，有库存，自弹式，约 11.6×10.5 mm 封装）**。原 MUP-M617-2 无库存。备选 TF PUSH C393941（深约 15 mm）、LCK-TF-110（15 mm）、TF-110（11.3 mm）因深度/板边不合适，放弃。
- **SD ESD 方案改为 2× TPD4E05U06DQAR（U12/U13，LCSC C138714，约 $0.082，库存约 9.4 万，IO 电容 0.5 pF）**，替换原来 7 颗分立 ESDLC5V0LB（D6–D12，约 3 pF/颗）。原因：
  - 0.5 pF 远低于 3 pF，对 SD_CLK 更友好；
  - 流通式（flow-through）封装可以让 6 根 SD 线直接穿过，不需要再绕线。
  - U12 接 SD_D2/D3/CMD/DET，U13 接 SD_CLK/D0/D1，U13 的 1/10 脚留空（数据手册允许）。
  - D13/D14（CC1/CC2）保留 ESDLC5V0LB。
- **SD 总线全部改为 F.Cu 0.127 mm 平行走线**，路径是 U2 → 45° 斜线 → U12/U13 → J5，**Y1 晶振投影区下方已没有任何 SD 线**（脚本检查过：Y1 区域内只剩 GND 过孔）。
- **改动和移动的元件：**
  - C13 移到 (28.4,28.85)，XOUT 走线变短。
  - C14（3V3 100 nF）原位置被 SD 总线占用，改放在 Q3 输入旁 (28.6,36.7)，作为 SD 电源开关的输入去耦。
  - C34（SOC_LDO_1V8 2.2 µF）由 0603 改为 0402 CL05A225MQ5NSNC（C12530，basic 库，$0.0054），放到 **B 面** (24.05,29.275)，避开 Y1 投影。
- **重布的网络：** PMIC_SDA、PMIC_SCL、PMIC_IRQ_N、PWRON_N、RTC_3V3、DRAM_1V5、SOC_LDO_1V8、SD_PWR_GATE、SD_3V3、SD_PWR_EN。
  - SD_3V3 从 J5.4 引出的颈部是 0.15 mm、长约 0.8 mm，夹在 CMD 与 DET 两个焊盘之间，没有更宽的空间；SD 卡峰值电流约 100–200 mA，这个宽度足够。
  - SD_PWR_EN 与原设计一样借用 In2 走一段（在 U2 下方 15.68,24.32 → 19.5,33.2）。这是低速静态使能信号；In2 是电源层，不是参考地，DRC 确认没有产生孤岛或未连接。
- 检查结果：DRC 0 违规 / 0 未连接 / 0 原理图一致性问题；ERC 0；power_contract、fel_recovery、usb_routing、wake_domain 全部通过。输出在 `verification/preflight_j5_20261015/`。

## U10 TPS65631 改由 3V3 供电（2026-10-15）

- **原因：**
  - TPS65631 输入范围是 2.9–4.5 V（TI SLVSBK1E §7.3），绝对最大 6 V。
  - VSYS 在插着 USB 或充电时可能超过 4.5 V，所以改用稳定的 3V3（AXP2101 DCDC1）。
- **改动：**
  - U10-11（AVIN）、U10-12（PVIN）、L5.1（升压电感输入）以及原 VSYS 小岛（含过孔）全部改为 3V3，与 VSYS 主网断开。U1 的 VSYS 引脚不受影响。
  - **3V3 取点：** 在 U10 上方新增 2 个 3V3 过孔 (7.25,46.75)、(8.05,46.75)，打到 In2 的 3V3 铜皮（离 U2、Y1 很远）。F 面用 0.4 mm 线接到 U10-12/11。L5 的 B 面供电线由 0.18 mm 加宽到 0.3 mm；靠近 GND 过孔 (7.76,44.18) 的那一小段只能做到 0.2–0.25 mm。
  - **输入电容：**
    - C46、C47 由 0603 改为 0402 10 µF CL05A106MQ5NUNC（C15525，basic，$0.0257）。
    - 新增 C59 100 nF（C1525）。
    - 三颗都放在 **B 面 U10 正下方**，紧挨 3V3 过孔，焊盘到 U10-11/12 的距离 ≤1 mm（≤2 mm 要求）。
    - 原来顶面 C46 的位置被 ELVSS 走线隔开，没法近距离接到 U10。
    - 数据手册推荐 2×10 µF，本方案满足。
- **软启动：** 数据手册 §8.3.3 说明，CTRL 拉高后升压级先以较低的开关电流限值启动（软启动，限制浪涌），10 ms 后负压级才启动。关断时（CTRL=0）输出与输入断开并主动放电，关断电流 0.1 µA。R35 把 LCD_EN 默认下拉为低，所以上电时 U10 不工作。**结论：不需要额外的负载开关。**
- **AXP2101 DCDC1 电流预算：**
  - DCDC1 额定 2 A。
  - U10 典型负载（屏幕约 100 mA@4.6 V / −4 V，效率约 85%）时，3V3 输入约 0.3 A；数据手册满载（各 300 mA）最坏约 1.0 A。
  - 加上 SoC IO、SD 卡（峰值约 0.2 A）等其余负载，最坏合计约 1.4–1.5 A，低于 2 A。
  - 需要实测确认屏幕全白画面的电流。
- 检查：DRC 0/0/0，ERC 0，四项静态检查通过（`verification/preflight_u10_20261015/`）。

## 2026-10-15 · 0Ω 电源隔离链接（R36–R40）
- 在 AXP2101 每路输出与负载之间加 0402 0Ω（0402WGF0000TCE，C17168，basic，≈$0.0011）。成本几乎为零，可逐路隔离短路/OTP 错误。
- 3V3 分为两路：R39（B 面，主干，经新 3V3 via (16.1,49.95) 进入 In2 3V3 带）、R38（北支路 3V3_B）。原因：两片负载区在 U2 下方无法在负载侧互连（布线失败），因此各自从 PMIC 侧取电。3V3_B 原有 0.18 mm 线段仍偏细（负载 Q3/U2.5/U2.78/D1，电流小），列入 OPEN_ISSUES。
- 反馈点保持在 PMIC 侧（U1.4/U1.9），断链接时 PMIC 可空载上电。
- R40 原放在 FPC_MATING_PROVISIONAL keepout 内，移至 (24.6,44.5) 90°，不放宽规则。
- ERC：1V8_PMIC 由 U1.18（power_out）驱动，不能加 PWR_FLAG；改为对负载侧 1V8 加 SUPPLY_SOURCE 标记（EXTRA_SUPPLY_NETS）。
- 修复：footprint 复制（pcbnew.FOOTPRINT(src)）会复制 UUID，导致 DRC 报错张冠李戴；已为 10 个重复的 footprint 重新生成 UUID。
- 流程见 BRINGUP_CN.md。验证：verification/preflight_links_20261015（DRC 0 / ERC 0 / unconnected 0 / parity 0，power_contract / fel / usb / wake 全部 True）。

## 2026-10-15 · U2 左上角去耦（pin 44 / 47 / 37）
- F 面 U2 左上角无空间（U2 courtyard 到 12.76/22.75，C31/R4/R5 紧邻），按指示改在 B 面。
- 拆除并重布 B 面 STATUS_LED、UART0_RX、WAKE_PULSE_N、KEY_BACK（全部低速 GPIO）。KEY_BACK 35.6→39.6 mm，多 2 个 via；其余长度基本不变。
- 新增 C60 100nF（CL05B104KO5NNNC，C1525，basic）B 面 (12.93,21.78)，经新 3V3 via (13.7,20.915) 接 pin 44 扇出；原最近电容 C57 6.4 mm。
- 新增 C62 100nF（C1525）B 面 (19.43,24.3)，经 B 走线接 pin 37 的 1V8 via (16.75,22.9)；原最近电容 C17 8.2 mm（布线距离约 3 mm）。
- pin 47：F 面 3V3 走线 47→55 约 2.6 mm，与 pin 55 共用 C57（B 面，经 via 12.8,28.3）。再加电容需拆 PMIC_SDA/SCL/FEL_KEY_N，风险大于收益，暂不做，记录在 OPEN_ISSUES。
- 验证：verification/preflight_u2dec_20261015，全部 0。

## 2026-10-15 · 丝印 pin-1 圆点与二极管极性
- 在库 footprint（sameat.pretty）与板上实例同时加入 F.SilkS 标记，避免 lib_footprint_mismatch：
  - pin-1 实心圆点（Ø0.3 mm）：U1、U2、U4、U5、U6、U8、U9、U10、U11、U12/U13、Q1–Q3、J2、J3、J4、J5、Y1。位置由脚本在所有实例上同时检查：与任何焊盘/丝印 ≥0.16 mm、离板边 ≥0.3 mm。
  - 阴极条（0.15 mm 线）：D1/D5 LED0603 在 pin 2（阴极，pin 1 = 阳极 3V3_B / STATUS_LED_A）；D2/D3 SOD-123 在 pin 1（阴极接 RTC_INT_N / ACCEL_INT_N，WAKE_REQ_N 为阳极侧）。
  - D13/D14 ESDLC5V0LB 为双向 TVS（Yangjie 规格书：Bidirectional，无极性标记），不加极性标记。
- L1–L3/L5/L6 电感、J1 USB-C 无方向要求。
- 注意：D2/D3 仍无 MPN/LCSC（见 OPEN_ISSUES），阴极映射需按最终选型的 SOD-123 规格书再次确认。
- 验证：verification/preflight_silk_20261015，全部 0。
