# 四层分区供电候选

2026-10-02：**USB 差分布线候选已完成并同步原理图。** 正反插对应路径的名义长度差约 0.40 / 0.38 mm（B 方向包含按 1.0 mm 板厚计的过孔）；ERC、DRC 和一致性检查均为 0。USB 主干保持顶层，B7 重复触点使用底层短支路。实际阻抗和实板验证尚未完成，见 [USB 修复说明](USB_ROUTING_REPAIR_CN.md)。当前检查目录 `verification/usb_routing_20261002/`。

2026-10-01：**自动唤醒定时阻容已改为 910 kΩ / 3.3 µF，名义脉宽约 3 s。** 原理图及 PCB 已同步，ERC、DRC 和一致性检查均为 0 问题。全温/偏压脉宽及重复触发仍需实测和固件配合，见 [自动唤醒修复](WAKE_PULSE_REPAIR_CN.md)。该次检查目录 `verification/wake_pulse_20261001/`。

2026-09-24：**屏幕 RESET / TE 已迁到 PA8 / PA9 的 1.8 V 电源域，并增加复位下拉 R32。** 主 PCB 与原理图已同步；当前 116 个电气器件，ERC、DRC、原理图一致性检查均为 0 问题。固件需要同步迁移引脚，实板点屏仍待验收。见 [屏幕逻辑电平修复](DISPLAY_IO_REPAIR_CN.md)，该次报告目录 `verification/display_io_20260924/`。

2026-09-21：**TF 默认上电电路已修复，原理图/PCB 已同步；最新 ERC、DRC、原理图一致性检查均为 0 问题。** 详见 [TF 供电修复](TF_POWER_REPAIR_CN.md)。实板启动及第一项 PMIC 默认配置仍待验证，尚未投板放行。该次报告目录为 `verification/tf_power_20260921/`，已由后续屏幕修复报告接续。

2026-09-20：**U1/U2 铜焊盘、EP 与钢网分窗已修复并同步本地库；最终主文件原生 DRC 为 0 未连接、0 违规、0 告警。当前为工程候选，尚未投板放行。**

打开本目录 `ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pro` 或 `.kicad_pcb`，并保留 `sameat.pretty` 与 `fp-lib-table`。

2026-09-20 电源复核补充：现已提供同名 `.kicad_sch`、四张子原理图及 `sameat.kicad_sym`/`sym-lib-table`，对应当前 115 个电气器件；四个机械孔只在 PCB 中。电源连接及采购要求见 [电源审查](POWER_REVIEW_CN.md)。**嘉立创 C3036461 的出厂电压/使能/时序尚未确认，电源冷启动仍未关闭。** 该次电源复核未修改 PCB；后续 TF 修复已修改 PCB。新增原生检查和逐脚比对位于 `verification/power_review_20260920/`，原有检查记录保留用于追溯。

## 本次修复

- U1 AXP2101：本体 5×5 mm、节距 0.40 mm；外围铜焊盘 0.70×0.20 mm、径向中心 ±2.40 mm；EP 3.40×3.40 mm，钢网 2×2 分窗。
- U2 V851S：本体 9×9 mm、节距 0.35 mm；外围铜焊盘 0.70×0.18 mm、径向中心 ±4.40 mm；EP 6.50×6.50 mm，钢网 4×4 分窗。
- 按新焊盘重新扇出，补齐供电/控制信号和接地连接，清理残线与多余过孔。C38 向下微移 0.40 mm，其余元件中心和旋转不变。
- 当前 120 个封装均在正面（新增 R32），逐引脚网络映射与原理图一致，NAND 保持删除，板框仍为 38×64 mm。此前 U4/U5/U6/U8/U9 的封装修正保持，详见 [封装核查记录](FOOTPRINT_REVIEW_CN.md)。
- MIPI、SD_CLK、晶振、LX/SW 保持 F.Cu；USB 主干也在 F.Cu，B7 重复触点现有两颗过孔及 1.0698 mm 的 B.Cu 支路。层别检查不代表高速性能合格。

## 层与验证

| 层 | 用途 |
|---|---|
| F.Cu | 元件、关键线路、局部供电及接地铜 |
| In1.Cu | GND，一个连续填充多边形，无信号走线 |
| In2.Cu | 分区供电、GND 及局部信号跨接 |
| B.Cu | 辅助信号、局部供电及接地铜 |

TF 修复后 In2 的走线总长为 73.2963 mm（修复前 67.5065 mm），含供电和信号；本次变化见 `verification/tf_power_20260921/change_audit.json`，旧 `verification/assessment.json` 仅反映前一版本。这会改变电源铜区形状，实际载流及回流路径仍需结合电流和层叠审核。

KiCad 10.0.6 按原工程规则检查，未改变规则、降低严重级别或新增豁免。GND 和六个复查电源网络的焊盘各为一个连通组。旧版本二维几何统计见历史报告；C23 已改为 0805；本次 C47/U9 移位后的装配边界与间距以 USB 修复的原生 DRC 为准。

## 文件与追溯

- [四层预览](four_layers.png)，当前四个原生 SVG 位于 `verification/usb_routing_20261002/layers/`。
- `verification/usb_routing_20261002/drc.json`、`provenance.json`：与当前主文件哈希对应的 DRC；显示、TF 修复目录和旧根目录同类报告为历史记录。
- `verification/geometry_audit.json`、`assessment.json`：前一版本的几何、引脚网络、层别、铜线长度及摆件记录；后续差异分别由 `tf_power_20260921/change_audit.json` 和 `display_io_20260924/change_audit.json`、`wake_pulse_20261001/change_audit.json` 及 `usb_routing_20261002/change_audit.json` 记录。
- `verification/u1_u2_repair_audit.json`：本次封装、钢网、网络与接地核查。
- `verification/usb_routing_20261002/via_in_pad_audit.json`：当前 38 处钻孔/SMD 焊盘相交，涉及 37 个过孔，仍须确认填孔封帽和装联工艺。旧根目录同名报告为修复前记录。
- `verification/u1u2_repair_20260919/before_promotion/`：本轮覆盖前的 PCB、两个 QFN 库和旧报告备份；同级过程检查点仅供追溯。

本轮 land 是根据厂家机械图制定的工程设计，仍需装联资格确认；高速差分线、实际层叠/载流、J4 机械接口及功能验收的未完成项见 [验收记录](OPEN_ISSUES_CN.md)。新增原理图用于连接审查，不能替代电源默认配置或实板验证。没有生成生产 Gerber 或提交生产订单。
