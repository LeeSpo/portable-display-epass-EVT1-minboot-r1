# 四层分区供电候选

2026-09-11：**布线连通和本轮封装修正已保存；原生 DRC 为 0 未连接、0 违规、0 告警。当前仍是工程候选，不是投板放行版本。**

打开本目录 `ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pro` 或 `.kicad_pcb`。主 PCB 已更新，项目本地封装库为 `sameat.pretty`，请随工程保留。

## 已完成

- 补齐核心电源、接地铜区及 SD/控制信号连接，修复热连接、残线和过孔端点问题。
- 按厂家资料重建 U4 LIS2DW12 的 4-2-4-2 焊盘排列和 U5 RV-3028-C7 的横向两排焊盘，恢复相关走线。
- U6、U8、U9 使用本器件对应的推荐 land；U1/U2 修正真实本体的 F.Fab 轮廓。细节、图纸页码及未确认项见 [封装核查记录](FOOTPRINT_REVIEW_CN.md)。
- 清理并重布 U9—J1 附近的 USB 路径。关键 MIPI、USB、SD_CLK、晶振、LX/SW 网络仍全部位于 F.Cu，无换层过孔；这只是层别检查，高速约束尚未签核。
- 保留主工程 L2/C6/C7 的位置；为封装间距及走线调整 C14、C16、C26、C34、D10、R1、U8、U9。完整前后坐标见 `verification/assessment.json`。
- 119 个封装均在正面，NAND 保持删除，逐引脚网络映射一致；38×64 mm 板框及安装孔位置保持不变。

## 层与验证

| 层 | 当前用途 |
|---|---|
| F.Cu | 元件、关键线路、局部供电与接地铜 |
| In1.Cu | GND，保存后为一个连续填充多边形，无信号走线 |
| In2.Cu | VSYS、3V3、CORE_0V93、DRAM_1V5、1V8 电源区、GND 和少量局部信号跨接 |
| B.Cu | 辅助信号及局部供电与接地铜 |

部分 In2 电源区被间隙/局部线路分成多个填充多边形；已通过其他铜层及过孔连通。GND 与六个复查电源网络的所有焊盘各属一个连通组，并由原生 DRC 确认没有未连接项。不能把多边形数或连通结果当作载流能力证明。

KiCad 10.0.6 原生检查采用原有工程规则，未降低严重级别或增加豁免。二维几何检查通过：最小 courtyard 间距 0.302076 mm，不同网络焊盘最小间距 0.15 mm，未发现庭院/焊盘重叠或进入预留区。

## 交付文件

- [四层预览](four_layers.png)，以及 `verification/layers/` 的四个 KiCad 原生 SVG。
- `verification/drc.json` 和 `drc_provenance.json`：最终主板的 DRC、版本与文件哈希。
- `verification/geometry_audit.json`：二维几何与引脚网络映射。
- `verification/assessment.json`：关键网络层别、铜线总长、铜区和最终摆件变动。
- `verification/via_in_pad_audit.json`：钻孔与 SMD 焊盘相交位置。
- `verification/routing_20260910/main_before_promote_20260911.kicad_pcb`：覆盖主板前的完整备份；该目录其余文件为过程检查点，不能替代最终 `verification/drc.json`。

U1/U2 推荐焊盘、高速差分线、焊盘内过孔工艺、实际层叠/载流、J4 机械接口及原理图/ERC 仍需验收，见 [未完成项](OPEN_ISSUES_CN.md)。尚未生成或提交生产订单。
