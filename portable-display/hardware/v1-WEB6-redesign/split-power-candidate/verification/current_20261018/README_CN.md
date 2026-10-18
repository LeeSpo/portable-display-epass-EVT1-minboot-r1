# 当前源文件验证（2026-10-18）

**工程候选，未放行生产。** 本轮正式验证在不含旧报告的隔离副本运行，未保存或修改维护中的 PCB、原理图、规则和库。此前的受控编辑/填铜保存在临时编辑副本完成，通过后才同步硬件源；两个步骤分别记录。

- 基线 PCB：`0409c89016cf30fdbe9049a122eb806341be229a87bc2f33c1adee9fbf4404a1`。
- 当前 PCB SHA-256：`514d29a0e2d06c731260da512aed54bfc88a098491cf9f4e367444c9fee9d8cc`；KiCad 10.0.6。
- [provenance.json](provenance.json) 记录全部硬件/工具源哈希、原生命令、退出码和源文件未变检查。
- [optimization_audit.json](optimization_audit.json) 记录基线对照：全部原有封装的位置/层/值/料号/焊盘保持；新增仅 C64 与 TP1–TP10；规则、板框和叠层保持。

| 检查 | 结果 |
|---|---|
| [ERC](erc.json) | 0 违规 |
| [保存铜皮 DRC](saved_fill_drc.json) | 0 违规 / 0 未连接 / 0 原理图一致性问题 |
| [重新填铜 DRC](drc.json) | 0 违规 / 0 未连接 / 0 原理图一致性问题 |
| [电源及网表逐脚比对](power_contract.json) | 通过；143 个电气对象 / 555 个编号焊盘 / 204 项电源脚约束 |
| [FEL](fel_recovery.json)、[USB](usb_routing.json)、[唤醒域](wake_domain.json) | 全部通过 |
| [唤醒故障注入](negative_checks.json) | 6 种错误全部被拒绝 |
| [生产包回归](package_negative_checks.json) | 25 个有效/无效案例全部符合预期，覆盖坐标、角度、料号、数量、排除标记和跨版本来源等 |
| [生成器烟测](generator_smoke.json) | 隔离重生 143 个符号；ERC 0，网表与 PCB 逐脚一致；详见报告中的重现性说明 |
| [生产包完整性](package_integrity.json) | 54 行 BOM、131 颗，117 正面 / 14 背面；逐颗核对 BOM 字段及 CPL 坐标/面/角度，并记录全包哈希 |

过孔铜环与 SMD 铜焊盘重叠的数量由 33 变为 31，钻孔进入 SMD 焊盘由 26 变为 23。外移三处旧孔，同时 C64 的新 GND 孔铜环与其焊盘角落略有重叠，钻孔未进入焊盘；仍须全孔 POFV。上述统计按正面积相交计算，清单见优化审计。

## 复现

在工程目录运行（输出目录须不存在或为空）：

```sh
python3 tools/verify_candidate.py --output /tmp/split-power-check --package verification/production_20261018
```

省略 `--package` 时要求 `verification/` 中恰好保留一个 `production_*` 目录，避免误选旧包。安装依赖与 KiCad 路径见 [工程说明](../../README_CN.md)。

[新生产预览包](../production_20261018/README_CN.md) 来自相同源板；旧报告和包由 Git 历史恢复，不再作为当前证据。静态通过仍不代表冷启动、实板点屏、装联验收或制造放行，详见 [未完成项](../../OPEN_ISSUES_CN.md)。
