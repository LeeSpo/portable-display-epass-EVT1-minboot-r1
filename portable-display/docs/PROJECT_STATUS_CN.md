# 项目进展与恢复索引（2026-10-18）

## 当前成果

维护入口为 [split-power-candidate](../hardware/v1-WEB6-redesign/split-power-candidate/README_CN.md)：38 × 64 mm 四层自研板、完整原理图、PCB、本地库和独立验证工具。硬件来自 `cae2016`，通过 `0fe1013` 导出 JLC 包，随后纳入 `WEB6-redesign` 的 `b14e0fb`。2026-10-18 在 `codex/optimize-v1-layout` 完成局部优化并重新导出，BOM/CPL 为 131 颗（117 正面 / 14 背面），仍未生产放行。

近期提交依次完成 PC1 FEL 恢复、LCD_EN 默认下拉、输入去耦及电池/TF/ESD 接口修正，之后完成 U10 供电、隔离链接、U2 背面去耦、丝印、部分焊盘内过孔外移、J4 定型、指定叠层和器件采购编号。

本轮新增 U2-47 独立去耦、十个裸测试点和电池线序丝印，改善 DSI D0N 拐角并外移三处非 EP 过孔；详见 [优化记录](../hardware/v1-WEB6-redesign/split-power-candidate/OPTIMIZATION_20261018_CN.md)。电源 OTP 冷启动、机械/FPC、装联资格、高速与实板验收仍未完成。详见 [当前未完成项](../hardware/v1-WEB6-redesign/split-power-candidate/OPEN_ISSUES_CN.md)。

## 分支与合并

| 整理前分支 | 提交 | 处理 |
|---|---|---|
| `main` | `8cff54b` | 旧基线，落后 WEB6 60 个提交；更新为整理结果 |
| `WEB6-redesign` | `b14e0fb` | 最新自研硬件，作为整理基线 |
| `board` | `0141ea9` | 较早 split-power 合并节点，没有独有文件增量；保留分支追溯 |
| `dev-board` | `13f46d0` | 合入其独有的 50 份 YuzukiHD-Lizard 文档与图片 |

整理通过 `codex/consolidate-main` 完成，结果合入 `main` 并推送 GitHub，默认分支统一为 `main`。其他分支保留，不重写已有提交历史。开发板资料与自研硬件分别作为参考资料和当前工程保存。

## 2026-10-17 清理记录

- 删除旧 `v0_legacy`、placement-only 工程、历史验证/路由中间稿、重复根工程和路由日志。
- 当前工程的解析、几何、USB 和原理图生成依赖迁入自身 `tools/`；原始芯片/连接器资料迁到统一 `reference/`。
- 清理时仅保留当时匹配 PCB 的生产预览包和验证。2026-10-18 的新包及[本轮验证](../hardware/v1-WEB6-redesign/split-power-candidate/verification/current_20261018/README_CN.md)已替换当时的证据，旧图片不标为当前预览。
- 开发板 ZIP 与展开的 50 个文件逐字节相同，保留展开文件；去除重复屏幕 PDF 和 V851S 表格。
- [逐文件删除清单](CLEANUP_20261017.json)记录 2071 个旧路径、原始 SHA-256、大小、来源提交，以及迁移和保留的硬件/生产包哈希。受管文件移除约 417 MiB；Git 历史仍保留这些内容。

该次清理保留的 72 个硬件源/生产包文件与清理前逐字节一致，当时没有修改硬件或重导。之后的 2026-10-18 优化修改了 PCB、原理图、本地库和生成器，并重导生产预览包；规则、叠层和板框保留。

## 当前验证边界

完整验证在不含旧目录的隔离副本运行。KiCad 10.0.6 的 ERC、重新填铜后 DRC/未连接/原理图一致性，以及电源/FEL/USB/唤醒检查和六项唤醒故障注入均已通过；生产包完整性回归共 25 个案例；BOM/CPL 与板上贴装位号逐一对照。

2026-10-17 的旧保存铜皮直接 DRC 为 329 项；2026-10-18 已在临时编辑副本受控填铜保存、同步源文件并重导生产预览包。正式验证不保存维护源文件，同时保留直接 DRC 和 `--refill-zones` 结果。新生产包逐颗核对 BOM 型号/封装/料号与 CPL 坐标/面/角度，并记录源文件及导出文件哈希。

## 恢复旧稿

自研历史固定在 [b14e0fb](https://github.com/LeeSpo/portable-display-epass-EVT1-minboot-r1/tree/b14e0fbead4cc5602254eedcb0fa77d3e3236ec2)，开发板原始资料固定在 [13f46d0](https://github.com/LeeSpo/portable-display-epass-EVT1-minboot-r1/tree/13f46d0ad2ac7986ad3beef088e6ad1adfc5d3a7)。清单的 `source_commit` 同时包含两者。

查看单个文件，不覆盖当前工程：

```sh
git show b14e0fb:portable-display/hardware/v0_legacy/README.md
```

恢复旧工程到独立临时目录：

```sh
mkdir -p /tmp/epass-history
git archive b14e0fb portable-display/hardware/v0_legacy | tar -x -C /tmp/epass-history
```

其他旧路径同样可使用清单中的完整路径从来源提交取回。历史检查仅对应原始源版本。
