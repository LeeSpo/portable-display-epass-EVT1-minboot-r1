# 项目进展与分支整理（2026-10-17）

## 当前成果

维护入口为 [split-power-candidate](../hardware/v1-WEB6-redesign/split-power-candidate/README_CN.md)：38 × 64 mm 四层自研板、完整原理图、PCB、本地库和独立验证工具。硬件来自 `cae2016`，通过 `0fe1013` 导出 JLC 包，随后纳入 `WEB6-redesign` 的 `b14e0fb`。BOM/CPL 为 130 颗（117 正面 / 13 背面），不是生产放行。

近期提交依次完成 PC1 FEL 恢复、LCD_EN 默认下拉、输入去耦及电池/TF/ESD 接口修正，之后完成 U10 供电、隔离链接、U2 背面去耦、丝印、部分焊盘内过孔外移、J4 定型、指定叠层和器件采购编号。

电源 OTP 冷启动、机械/FPC、装联资格、高速与实板验收仍未完成。详见 [当前未完成项](../hardware/v1-WEB6-redesign/split-power-candidate/OPEN_ISSUES_CN.md)。

## 分支与合并

| 整理前分支 | 提交 | 处理 |
|---|---|---|
| `main` | `8cff54b` | 旧基线，落后 WEB6 60 个提交；更新为整理结果 |
| `WEB6-redesign` | `b14e0fb` | 最新自研硬件，作为整理基线 |
| `board` | `0141ea9` | 较早 split-power 合并节点，没有独有文件增量；保留分支追溯 |
| `dev-board` | `13f46d0` | 合入其独有的 50 份 YuzukiHD-Lizard 文档与图片 |

整理通过 `codex/consolidate-main` 完成，结果合入 `main` 并推送 GitHub，默认分支统一为 `main`。其他分支保留，不重写已有提交历史。开发板资料与自研硬件分别作为参考资料和当前工程保存。

## 本次清理

- 删除旧 `v0_legacy`、placement-only 工程、历史验证/路由中间稿、重复根工程和路由日志。
- 当前工程的解析、几何、USB 和原理图生成依赖迁入自身 `tools/`；原始芯片/连接器资料迁到统一 `reference/`。
- 仅保留匹配当前 PCB 的生产预览包及 [本轮验证](../hardware/v1-WEB6-redesign/split-power-candidate/verification/current_20261017/README_CN.md)。旧图片不继续标为当前预览。
- 开发板 ZIP 与展开的 50 个文件逐字节相同，保留展开文件；去除重复屏幕 PDF 和 V851S 表格。
- [逐文件删除清单](CLEANUP_20261017.json)记录 2071 个旧路径、原始 SHA-256、大小、来源提交，以及迁移和保留的硬件/生产包哈希。受管文件移除约 417 MiB；Git 历史仍保留这些内容。

72 个保留的硬件源文件及生产包文件与清理前逐字节一致。生产包未重新导出，PCB、原理图、规则和库未修改。

## 验证边界

完整验证在不含旧目录的隔离副本运行。KiCad 10.0.6 的 ERC、重新填铜后 DRC/未连接/原理图一致性，以及电源/FEL/USB/唤醒检查和六项故障注入均已通过；BOM/CPL 与板上贴装位号逐一对照。

当前保存铜皮的直接 DRC 有 329 项，原生 `--refill-zones` 后为 0。两份报告同时保留，验证不保存源 PCB。重新填铜的检查通过不证明旧生产包与重新生成铜皮一致；制造放行前仍需受控保存、比较、验证及重新导出。

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
