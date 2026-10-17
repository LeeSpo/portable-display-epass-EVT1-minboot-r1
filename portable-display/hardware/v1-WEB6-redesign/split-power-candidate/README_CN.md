# 38 × 64 mm 四层 split-power 工程候选

更新：2026-10-17。**尚未放行生产。** 电源 OTP 冷启动配置、屏幕/FPC 装配与实板功能仍待确认，见 [未完成项](OPEN_ISSUES_CN.md)。

## 当前版本

硬件源来自 `cae2016`，已包含在 `WEB6-redesign` 的 `b14e0fb` 中。本轮整理不改 PCB、原理图、本地库、规则或生产包。

- PCB SHA-256：`0409c89016cf30fdbe9049a122eb806341be229a87bc2f33c1adee9fbf4404a1`。
- 136 个封装：132 个电气器件与 4 个安装孔；贴装 130 颗，正面 117 / 背面 13。R31 为 DNP，J3 为裸调试焊盘。
- 已完成 TF 默认供电、显示 RESET/TE 1.8 V 电平、约 3 s 自动唤醒、常供电中断隔离、PC1 FEL 恢复、U10 供电和 U2 去耦等工程修改。
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

工具在隔离副本运行原生 ERC、DRC、原理图一致性、网表逐脚约束、电源/FEL/USB/唤醒检查、六项故障注入及 BOM/CPL 对照，并检查源文件哈希未变。所有 Python 依赖都位于本工程，无需旧工程目录。

**DRC 必须重新填铜：** 当前保存铜皮的直接检查在 KiCad 10.0.6 上报告 329 项；`--refill-zones` 后为 0 违规、0 未连接、0 原理图一致性问题。验证工具同时保留直接检查诊断和重新填铜结果，不保存 PCB、不修改规则或增加豁免。重新填铜通过不证明原生产 Gerber 已复核；后续制造放行前还需核对保存铜皮及生产导出。

## 最新证据和生产预览

- [本轮验证](verification/current_20261017/README_CN.md)：含源文件哈希、工具版本、命令、原生报告、故障注入和生产包完整性检查。
- [2026-10-15 JLC 包](verification/production_20261015/README_CN.md)：BOM/CPL、Gerber 和钻孔，仅用于报价与预览，未重新导出、未放行。
- [采购/制造要求](ORDERING_GUIDE_CN.md)、[首次上电流程](BRINGUP_CN.md)、[电源审查](POWER_REVIEW_CN.md)、[屏幕装配评估](../../../docs/SCREEN_STACK_CN.md)。

旧验证目录已移到 Git 历史，现有修复说明明确作为历史决策记录；当前状态以本文、未完成项及本轮哈希匹配报告为准。[项目进展与恢复索引](../../../docs/PROJECT_STATUS_CN.md)。
