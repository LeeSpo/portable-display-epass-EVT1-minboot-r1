# 未完成项与验收记录

**状态：分区供电候选，未完成全部优化，不可投板。**

## 原生 DRC

候选 PCB SHA-256：`c98703585c7844f161dfef1c8fab4dfb2e216a1dbfe8a7644322f9c177577cb5`。对应工程文件、DRC 报告的哈希见 `verification/drc_provenance.json`。

未连接：**19 处**。未报告短路或铜间距违规；这不代表整板通过。

| 类型 | 数量 |
|---|---:|
| starved_thermal | 4 |
| track_dangling | 2 |
| track_not_centered_on_via | 4 |
| missing_courtyard | 4 |
| footprint_type_mismatch | 2 |
| lib_footprint_issues | 115 |

## 逐项未连接

以下为原生 DRC 输出的连接两端。GND 项表示不同铜区之间尚未连通，不能视为无关警告。

1. Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5} ↔ Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5}
2. Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5} ↔ Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5}
3. Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5} ↔ Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5}
4. Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5} ↔ Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5}
5. Zone [GND] on B.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5} ↔ Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5}
6. Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5} ↔ Zone [GND] on F.Cu, priority 0，位置 {'x': 0.5, 'y': 0.5}
7. Pad 75 [CORE_0V93] of U2 on F.Cu，位置 {'x': 17.125, 'y': 32.75} ↔ Track [CORE_0V93] on B.Cu, length 0.2638 mm，位置 {'x': 13.7983, 'y': 34.9562}
8. Pad 4 [CORE_0V93] of U1 on F.Cu，位置 {'x': 27.75, 'y': 51.1} ↔ Track [CORE_0V93] on B.Cu, length 9.3000 mm，位置 {'x': 17.5, 'y': 48.2}
9. Track [SD_DET] on F.Cu, length 1.7678 mm，位置 {'x': 31.65, 'y': 24.4} ↔ Track [SD_DET] on F.Cu, length 0.4056 mm，位置 {'x': 22.75, 'y': 27.825}
10. Track [SD_PWR_EN] on F.Cu, length 1.2000 mm，位置 {'x': 15.725, 'y': 23.25} ↔ Pad 1 [SD_PWR_EN] of R21 on F.Cu，位置 {'x': 24.5, 'y': 36.15}
11. Pad 1 [SD_D2] of D6 on F.Cu，位置 {'x': 28.6, 'y': 34.25} ↔ Pad 11 [SD_D2] of U2 on F.Cu，位置 {'x': 22.75, 'y': 28.175}
12. Pad 15 [LCD_TE] of J4 on F.Cu，位置 {'x': 13.6, 'y': 43.0} ↔ Pad 3 [LCD_TE] of U2 on F.Cu，位置 {'x': 22.75, 'y': 30.975}
13. Pad 16 [LCD_RST] of J4 on F.Cu，位置 {'x': 13.9, 'y': 39.935} ↔ Pad 2 [LCD_RST] of U2 on F.Cu，位置 {'x': 22.75, 'y': 31.325}
14. Track [SD_D1] on B.Cu, length 0.1000 mm，位置 {'x': 27.6, 'y': 31.5} ↔ Pad 6 [SD_D1] of U2 on F.Cu，位置 {'x': 22.75, 'y': 29.925}
15. Pad 1 [SD_D0] of D10 on F.Cu，位置 {'x': 24.1, 'y': 27.5} ↔ Pad 7 [SD_D0] of U2 on F.Cu，位置 {'x': 22.75, 'y': 29.575}
16. Pad 7 [SD_D0] of J5 on F.Cu，位置 {'x': 30.35, 'y': 29.5} ↔ Pad 1 [SD_D0] of D10 on F.Cu，位置 {'x': 24.1, 'y': 27.5}
17. Track [SD_CMD] on B.Cu, length 0.1000 mm，位置 {'x': 27.0, 'y': 28.6} ↔ Pad 9 [SD_CMD] of U2 on F.Cu，位置 {'x': 22.75, 'y': 28.875}
18. Track [SD_CMD] on F.Cu, length 0.0500 mm，位置 {'x': 28.6, 'y': 31.7} ↔ Track [SD_CMD] on F.Cu, length 0.7387 mm，位置 {'x': 29.6113, 'y': 33.5}
19. Track [PMIC_SCL] on F.Cu, length 0.2828 mm，位置 {'x': 15.5, 'y': 19.7} ↔ Track [PMIC_SCL] on F.Cu, length 0.2512 mm，位置 {'x': 16.075, 'y': 23.25}

## 电源、信号与制造限制

- 五个 In2 电源网络各有一个保存后的填充多边形；In1 GND 有一个填充多边形。这个检查证明铜区形态连续，不证明所有芯片电源引脚均已接入。
- 核心电源仍有未完成接入，详见上面的原生 DRC。所有电源在通电前必须完成连通复核。
- 主电源铜线已在几何间距允许处加宽，但保留细颈；`verification/power_widths.json` 列出外层铜线宽度统计。尚无各路峰值电流和板厂铜厚/介质层数据，未完成压降、载流和温升验算。
- MIPI 两对线路均在顶层，但尚未完成并行耦合与长度匹配：时钟两线总铜长约 7.860 / 15.235 mm，数据两线约 8.060 / 20.635 mm，不能按合格差分线交付。
- USB 两网均在顶层，但包含多个端点和支路；总铜线长度不能直接当作端到端差分偏斜。还需按 U2—U9—J1 的具体路径重新检查耦合、支路和阻抗。
- U1、U10 暴露接地焊盘中增加了 0.60/0.30 mm 接地过孔。必须在制造资料中确认塞孔/填孔、背面阻焊及钢网方案，防止焊料流失；当前未完成装联签核。
- 4 处热连接不足涉及 J1 屏蔽固定脚和 J3 接地脚；需修复热焊盘周围铜区，不能通过降低 DRC 要求消除。
- 115 条库封装问题未逐一与制造商图纸核对完成；4 个安装孔缺少显式 courtyard；J1/J3 混合焊盘与封装类型属性不一致。均保留在报告中。
- 板框仍为 38 × 64 mm、标称板厚仍为 1 mm；没有把未确认的铜厚和介质厚度填成已验证层叠。
- J4 仍为装配占位。屏幕架高方案的 FPC 对位、触点面、支撑高度和干涉检查尚未完成；没有同步到本候选的原理图/ERC 签核。

## 完成验收所需的后续工作

1. 优先补齐核心电源和剩余信号连接，消除接地铜区断连、热连接不足及残线。
2. 联合 J4 最终位置重新布置 MIPI/USB 差分路径；不能仅通过增加一条蛇形线代替耦合与回流检查。
3. 取得板厂实际层叠、铜厚和各路设计电流，验证线宽瓶颈、过孔能力与阻抗。
4. 完成屏幕装配、封装尺寸和原理图一致性检查，然后对最终文件重新铺铜、运行原生 DRC 并更新全部哈希。
