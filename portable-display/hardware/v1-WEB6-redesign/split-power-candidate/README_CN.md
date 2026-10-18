# 38 × 64 mm 四层 split-power 工程候选

更新：2026-10-18。**尚未放行生产。** 电源 OTP 冷启动配置、屏幕/FPC 装配与实板功能仍待确认，见 [未完成项](OPEN_ISSUES_CN.md)。

## 当前版本

硬件基线来自 `cae2016`，经 `b14e0fb` 纳入主线。本轮在 `codex/optimize-v1-layout` 优化局部布线、去耦和调试接口，保持全部功能、板框、叠层与规则。详见 [本轮优化记录](OPTIMIZATION_20261018_CN.md)。

- PCB SHA-256：`514d29a0e2d06c731260da512aed54bfc88a098491cf9f4e367444c9fee9d8cc`。
- 147 个封装：143 个电气对象与 4 个安装孔；贴装 131 颗，正面 117 / 背面 14。R31 为 DNP，J3 和 TP1–TP10 为裸调试焊盘。
- 已完成 TF 默认供电、显示 RESET/TE 1.8 V 电平、约 3 s 自动唤醒、常供电中断隔离、PC1 FEL 恢复、U10 供电和 U2 去耦等工程修改。
- 本轮增加 U2-47 独立去耦 C64、十个裸测试点和电池线序丝印，外移三处非 EP 过孔，并把 DSI D0N 的 16 个直角改为 45° 转折。
- 叠层为 JLC04101H-3313，4 层、1.0 mm；USB/DSI CK 成对走线，DSI D0 仍采用两根独立走线。残留焊盘内过孔按 POFV 要求处理，均仍需制造及实板验证。

## 打开和验证

用 KiCad 10 打开本目录的 `ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pro`。保留 `sameat.pretty`、`sameat.kicad_sym` 及两个库表；库引用使用 `${KIPRJMOD}`。

在本目录运行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/verify_candidate.py --output /tmp/split-power-check
```

输出目录必须不存在或为空。原生检查需 `kicad-cli`；可用 `--kicad-cli /absolute/path/to/kicad-cli` 或环境变量 `KICAD_CLI` 指定。macOS 自动回退到 `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`。

工具在隔离副本运行原生 ERC、DRC、原理图一致性、网表逐脚约束、电源/FEL/USB/唤醒检查、六项唤醒故障注入、25 个生产包完整性回归案例及 BOM/CPL 逐项对照，并检查源文件哈希未变。所有 Python 依赖都位于本工程，无需旧工程目录。

**填铜与导出：** 本轮在临时编辑副本受控保存 KiCad 10.0.6 原生填铜，再同步通过检查的源文件并重导生产预览包。正式验证仍在隔离副本执行 `--refill-zones`，同时保留保存铜皮的直接 DRC，不保存维护源文件、不修改规则或豁免。两种检查均应为 0 违规、0 未连接、0 原理图一致性问题；结果和哈希见本轮报告。

## 最新证据和生产预览

- [本轮验证](verification/current_20261018/README_CN.md)：含源文件哈希、工具版本、命令、原生报告、故障注入和生产包完整性检查。
- [2026-10-18 JLC 包](verification/production_20261018/README_CN.md)：从本轮源文件重导的 BOM/CPL、Gerber、钻孔与正反面预览；仅用于报价与工程预览，未放行。
- [采购/制造要求](ORDERING_GUIDE_CN.md)、[首次上电流程](BRINGUP_CN.md)、[电源审查](POWER_REVIEW_CN.md)、[屏幕装配评估](../../../docs/SCREEN_STACK_CN.md)。

旧验证目录已移到 Git 历史，现有修复说明明确作为历史决策记录；当前状态以本文、未完成项及本轮哈希匹配报告为准。[项目进展与恢复索引](../../../docs/PROJECT_STATUS_CN.md)。
