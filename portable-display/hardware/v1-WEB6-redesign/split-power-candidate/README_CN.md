# 四层分区供电候选

**已实现分区供电结构，尚未完成全部优化与验收，不可投板。**

打开本目录的 `ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pro` 查看候选。
原目录中的 `ak_display_38x64_PLACEMENT_ONLY.kicad_pcb` 未覆盖；此前原板备份保存在上级目录的 `verification/power_optimization/`。

## 已落地的改动

| 层 | 当前保存的设计 |
|---|---|
| F.Cu | 元件、关键线路、局部供电和接地铜 |
| In1.Cu | 完整 GND，填充后为一个连续多边形 |
| In2.Cu | VSYS、3V3、CORE_0V93、DRAM_1V5、1V8 五个独立电源铜区；其余区域接地 |
| B.Cu | 辅助信号、局部供电和接地铜 |

- 保留 NAND 删除状态，119 个封装及其引脚网络与既定映射一致。
- 延续 U1/U2 周围的摆件调整，板框、孔位和接口引脚定义不变。全部封装仍在 F.Cu。
- 五个主要供电区按实际过孔接入和负载分布构建；保存并填充后，各电源区均为一个多边形。局部供电网络保持独立，没有合并同电压但不同来源的网络。
- MIPI、USB、SD 时钟、晶振和五个 LX/SW 开关网络的铜线均在顶层，均没有跨层过孔。**所在层检查通过，不代表差分耦合、时序或阻抗已经通过。**
- 在几何间距允许处加宽电源线路，补充部分接地过孔并清理残线。主电源到负载的接入仍有未完成项。

## 实际检查结果

KiCad 10.0.6 原生 DRC：**19 处未连接、4 处热连接不足**。未报告短路或铜间距违规；另有残线、过孔端点和封装相关告警。没有调整 DRC 严重级别或添加豁免来隐藏这些问题。

二维摆件检查通过：最小 courtyard 间距 0.35 mm，不同网络焊盘最小间距 0.17 mm；未发现庭院重叠、焊盘重叠或元件进入预留区。此检查不覆盖三维装配。

MIPI 长度匹配、USB 路径与支路、实际阻抗、供电压降/载流、封装核对及屏幕机械配合尚未完成。完整列表见 [未完成项与验收记录](OPEN_ISSUES_CN.md)。

## 文件索引

- [四层彩色预览](four_layers.png)：来自当前保存的 PCB，颜色区分五个电源网络。
- `verification/layers/`：KiCad 原生导出的四个铜层 SVG。
- `verification/drc.json`：原生 DRC 明细。
- `verification/drc_provenance.json`：候选 PCB、工程文件和 DRC 报告的 SHA-256。
- `verification/geometry_audit.json`：二维摆件与引脚网络映射检查。
- `verification/assessment.json`：保存后铜区数量、面积、关键网络层别和铜线总长。
- `verification/power_zone_plan.json`：生成阶段的分区多边形与未直接纳入铜区的过孔。以保存后的 PCB 和原生 DRC 为准。
- `verification/power_widths.json`：最后一轮外层电源加宽记录及细颈统计，不是载流能力签核。

屏幕架在正面元件上方的结构评估见上级 `SCREEN_STACK_CN.md`；J4 仍为占位，不能据此认定排线已经适配。
