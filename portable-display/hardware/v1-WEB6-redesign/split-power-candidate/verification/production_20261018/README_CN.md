# JLC 工程预览包（2026-10-18）

**工程候选，未放行生产。** 从本轮已受控保存填铜的源文件重新导出，用于报价、DFM 和装配预览；PMIC OTP、屏幕实物、装联和实板验收仍未关闭。

- PCB SHA-256：`514d29a0e2d06c731260da512aed54bfc88a098491cf9f4e367444c9fee9d8cc`。
- KiCad 10.0.6；完整源哈希和导出命令见 [export_provenance.json](export_provenance.json)。导出未修改硬件源文件。
- [BOM_JLC.csv](BOM_JLC.csv)：54 行，131 颗，全部有 LCSC 字段；新增 C64 复用 C1525。
- [CPL_JLC.csv](CPL_JLC.csv)：131 颗，正面 117 / 背面 14。坐标为 KiCad 绝对 X、取负 Y、原始封装角度；未减辅助原点或镜像背面角度，须在工厂预览中核对针 1 和极性。
- R31 为 DNP；J3、TP1–TP10 为裸板调试焊盘，不采购、不贴装，不进入 BOM/CPL。测试点没有锡膏开口。
- [gerber_jlc.zip](gerber_jlc.zip)：四层铜、正反面阻焊/锡膏/丝印、板框及 PTH/NPTH 钻孔与钻孔图。原文件保留于 `gerber/`。
- [正面预览](preview/front_assembly.png) / [背面预览](preview/bottom_assembly.png)：由当前板的 Mask、Fab、Silk、Edge 层生成；背面已镜像。预览包含工艺图层，不是三维实物图。
- `checks/` 保留导出时 ERC、DRC、网表与四项电路约束检查；正式隔离验证见 [current_20261018](../current_20261018/README_CN.md)。
- [SHA256SUMS.txt](SHA256SUMS.txt) 覆盖本包其余文件；完整验证另记录全包哈希。

## 报价输入

38 × 64 mm、四层、1.0 mm、JLC04101H-3313、ENIG；全部 0.30 mm 过孔按 POFV 树脂塞孔并电镀封帽要求询价；双面标准型贴片。不能为压价删除背面去耦或改为普通开放通孔。

目标交货数量为 **2 PCS 完整单板 PCBA**；不要将 `3×2` 拼板的 `2 SET` 当作两块单板。PCB 裸板数量、工厂拼板和 SMT 交货数量应分别确认。按 [下单要求](../../ORDERING_GUIDE_CN.md)复核全部工艺与方向；本包不承诺 600 元总价，也不表示制造放行。
