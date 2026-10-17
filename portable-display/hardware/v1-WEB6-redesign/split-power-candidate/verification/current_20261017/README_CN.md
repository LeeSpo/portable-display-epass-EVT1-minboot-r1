# 当前源文件验证（2026-10-17）

**工程候选，未放行生产。** 本轮在不含旧目录的隔离副本运行，未保存或修改维护中的 PCB、原理图、规则和库。

- 硬件来源：`cae2016`，已纳入 `b14e0fb`；独立工具迁移提交：`74cec3a`。
- KiCad：10.0.6。PCB SHA-256：`0409c89016cf30fdbe9049a122eb806341be229a87bc2f33c1adee9fbf4404a1`。
- [来源及命令](provenance.json)记录全部硬件/工具源哈希、原生命令、退出码和源文件未变检查。

| 检查 | 结果 |
|---|---|
| [ERC](erc.json) | 0 违规 |
| [DRC，重新填铜](drc.json) | 0 违规 / 0 未连接 / 0 原理图一致性问题 |
| [电源约束与网表逐脚比对](power_contract.json) | 通过；132 电气器件 / 543 编号焊盘 / 202 项电源脚约束 |
| [FEL](fel_recovery.json)、[USB](usb_routing.json)、[唤醒域](wake_domain.json) | 全部通过 |
| [唤醒故障注入](negative_checks.json) | 6 种错误全部被拒绝 |
| [生产包故障注入](package_negative_checks.json) | 缺件、重复位号、缺 LCSC 和跨版本来源四项均被拒绝 |
| [原理图生成器迁移检查](generator_smoke.json) | 临时副本重生成 132 个符号，ERC 0，网表与原 PCB 逐脚一致 |
| [生产包完整性](package_integrity.json) | BOM/CPL/板上贴装位号一致；54 行 BOM、130 颗，117 正面 / 13 背面；记录全部生产包哈希 |

## 保存铜皮的诊断

[直接 DRC](saved_fill_drc.json)报告 329 项，未连接和原理图一致性均为 0；对应退出码 5。该诊断独立保存，未被抹去或改规则。

原生 `--refill-zones` 重新计算后检查全部为 0。该步骤不使用 `--save-board`，维护源文件哈希保持不变。此结论不证明 2026-10-15 原生产 Gerber 已与重新填铜结果核对；放行前须受控保存、比较、验证及重新导出。

## 复现

在工程目录运行（输出路径须不存在或为空）：

```sh
python3 tools/verify_candidate.py --output /tmp/split-power-check
```

安装依赖与 KiCad 路径见 [工程说明](../../README_CN.md)。本目录其余日志保留原始工具输出，临时路径只是隔离检查位置。静态连通、几何和网表通过均不代表实板功能、冷启动或生产放行，见 [未完成项](../../OPEN_ISSUES_CN.md)。
