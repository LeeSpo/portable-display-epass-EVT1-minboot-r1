# 最小系统布线完成记录 · 2026-09-05

非显示最小系统已完成电气连通布线，并通过当前项目规则下的 KiCad 10.0.6 原生验证。此结论不包含制造、电气性能或实物启动放行。

## 检查结果

| 项目 | 修改前 | 修改后 |
|---|---:|---:|
| 非显示未连接项 | 35（15 个网络） | 0 |
| DRC 违规错误 / 警告，不含未连接表 | 1 / 104 | 0 / 0 |
| ERC 违规 | — | 0 |
| 原理图与 PCB 不一致 | — | 0 |
| 显示未连接项 | 16 | 16，沿用原有明确豁免 |
| 自动化测试 | 44 | 45，通过 |
| 走线段 / 过孔 | 835 / 368 | 1797 / 349 |

最终原生报告：`verification/native-20260905T074324Z-5a4357/status.json`。同目录包含原生 ERC、DRC、网表、重填后的独立工程副本及 SHA-256 记录。根目录 PCB 的 SHA-256 为 `1eca7f94a7c70aa5c66dfdc38238a4c0b31c0df7696c494fffa77aeda35281f0`。

## 完成的修改

补齐 PMIC_SDA、E907_RX、SD_D1、SD_PWR_EN、ADC_KEYS、KEY_DOWN、STATUS_LED、STATUS_LED_A、USB_DM，以及 CORE_0V93、DRAM_1V5、1V8、RTC_3V3、3V3、GND 等剩余连接。新走线切分的电源覆铜在每轮原生重填后复查，补齐 VBUS 和 R3/R4 的 3V3 上拉供电连接。

R4 附近原有小铜皮只能形成一个热焊盘连接辐条；移除该局部孤立铜皮并用实际走线供电，未降低热焊盘连接要求。VBUS 在 PMIC 附近增加约 1.83 mm 的 In2.Cu 局部跨线，其余新增布线使用表层与底层；In1.Cu 接地平面未增加信号走线。

USB 的 SoC 至 ESD 主干改为同一 B.Cu 通道上的并行线，公共中心路径约 81.41 mm，现有候选线宽 0.09 mm、中心间距 0.27 mm。移除了此前 DM 主干反复换层的路径。上述尺寸只是当前几何值，尚不构成差分阻抗或电气长度审签；端部、连接器分支和跨参考电源区域仍需结合板厂叠层审查。

清理原生报告指出的冗余过孔与末端残留线段，将背面工程警示文字移动到不与焊盘和板边冲突的位置。未移动器件、改变引脚网络、降低设计规则或扩大显示豁免。

U2 的 54 个非显示引脚均通过铜线到达同网过孔或另一目标焊盘：47 个具有过孔连接，7 个使用直接同层连接。静态检查据此接受有效的直接焊盘连接，不再要求为其保留悬空过孔；新增移除 XIN 铜线的负向测试，确认真正断开的引脚仍被拒绝。静态检查不代替原生覆铜连通验证。

## 查看与复查

打开根目录 `portable_display_epass.kicad_pro`；已重填的最终检查副本位于上述报告目录的 `checked_project`。源 PCB 有意不保存陈旧覆铜缓存，在 KiCad 中查看铜皮时执行重填。

布线预览：`verification/minboot_completion/board_layers.png`。机器摘要：`verification/minboot_completion/summary.json`。`routing_backlog.csv` 仍是忽略覆铜的几何分组统计，不能把其中的电源分组当作原生未连项。

```sh
.venv/bin/python -m unittest discover -s tools -p 'test_*.py' -v
.venv/bin/python tools/verify_evt1.py --kicad-cli /Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
```

布线辅助脚本只用于此工程的候选生成与清理；修改后必须重新执行完整原生验证。`complete_minboot.py` 的填充输入必须来自对应设计的原生重填结果。`route_usb_trunk.py` 专门处理当前 USB 主干。不能仅依据脚本返回值放行 PCB。

## 仍未完成

屏幕定版与显示布线；AXP2101 实际变体/OTP、电源时序、去耦短环路、载流、充电及热设计审查；板厂叠层和 USB/SD 阻抗、回流、时序审查；器件封装和制造审签；启动固件、设备树与首板限流上电验证。

`design/release_gates.json` 的人工审签仍为 open，`fabrication_released` 仍为 false，未生成新的 Gerber 或制造包。
