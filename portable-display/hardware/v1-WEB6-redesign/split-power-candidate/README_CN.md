# 四层分区供电候选

2026-09-20：**U1/U2 铜焊盘、EP 与钢网分窗已修复并同步本地库；最终主文件原生 DRC 为 0 未连接、0 违规、0 告警。当前为工程候选，尚未投板放行。**

打开本目录 `ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pro` 或 `.kicad_pcb`，并保留 `sameat.pretty` 与 `fp-lib-table`。

## 本次修复

- U1 AXP2101：本体 5×5 mm、节距 0.40 mm；外围铜焊盘 0.70×0.20 mm、径向中心 ±2.40 mm；EP 3.40×3.40 mm，钢网 2×2 分窗。
- U2 V851S：本体 9×9 mm、节距 0.35 mm；外围铜焊盘 0.70×0.18 mm、径向中心 ±4.40 mm；EP 6.50×6.50 mm，钢网 4×4 分窗。
- 按新焊盘重新扇出，补齐供电/控制信号和接地连接，清理残线与多余过孔。C38 向下微移 0.40 mm，其余元件中心和旋转不变。
- 119 个封装均在正面，逐引脚网络映射一致，NAND 保持删除，板框仍为 38×64 mm。此前 U4/U5/U6/U8/U9 的封装修正保持，详见 [封装核查记录](FOOTPRINT_REVIEW_CN.md)。
- MIPI、USB、SD_CLK、晶振、LX/SW 仍全部在 F.Cu，无换层过孔；层别检查通过不代表高速性能合格。

## 层与验证

| 层 | 用途 |
|---|---|
| F.Cu | 元件、关键线路、局部供电及接地铜 |
| In1.Cu | GND，一个连续填充多边形，无信号走线 |
| In2.Cu | 分区供电、GND 及局部信号跨接 |
| B.Cu | 辅助信号、局部供电及接地铜 |

In2 的走线总长由 14.2399 mm 增至 67.5065 mm，含供电和信号；具体网络长度见 `verification/assessment.json`。这会改变电源铜区形状，实际载流及回流路径仍需结合电流和层叠审核。

KiCad 10.0.6 按原工程规则检查，未改变规则、降低严重级别或新增豁免。GND 和六个复查电源网络的焊盘各为一个连通组。二维几何检查通过：最小 courtyard 间距 0.302076 mm，不同网络焊盘最小间距 0.15 mm，未进入预留区。

## 文件与追溯

- [四层预览](four_layers.png)，四个原生 SVG 位于 `verification/layers/`。
- `verification/drc.json`、`drc_provenance.json`：与最终主文件哈希对应的 DRC。
- `verification/geometry_audit.json`、`assessment.json`：几何、引脚网络、层别、铜线长度及摆件变化。
- `verification/u1_u2_repair_audit.json`：本次封装、钢网、网络与接地核查。
- `verification/via_in_pad_audit.json`：39 处钻孔/SMD 焊盘相交记录，涉及 38 个不同过孔，仍须确认填孔封帽和装联工艺。
- `verification/u1u2_repair_20260919/before_promotion/`：本轮覆盖前的 PCB、两个 QFN 库和旧报告备份；同级过程检查点仅供追溯。

本轮 land 是根据厂家机械图制定的工程设计，仍需装联资格确认；高速差分线、实际层叠/载流、J4 机械接口及原理图/ERC 的未完成项见 [验收记录](OPEN_ISSUES_CN.md)。没有生成生产 Gerber 或提交生产订单。
