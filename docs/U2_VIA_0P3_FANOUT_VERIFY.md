# U2 过孔 0.3 mm 扇出可行性验证（2.4″ AOD 假设）

> Branch: `feat/u2-via-0p3-fanout-verify`（从 `board` 拉出）  
> 状态：**已做自动化挪件 + 扩孔阵试改**；几何检查 PASS；**铜线未全量重连，不可投板**  
> 假设屏幕：约 **2.4″ AOD AMOLED**（RM690B0 / ICNA3312 族，外形约 39×52 mm），板框仍 **58×110 mm**

## 1. 问题回顾

当前 EVT1 基线：`via pad 0.40 / drill 0.20`。  
U2 附近已是 dogbone + 错位扇出。仍用 0.2 是因为扇出环过孔过密。

## 2. 空间结论

- 板边：够（U2 居中，环外约 16 mm）
- 现布局：C35/Y1 等在 ~10 mm 圈挡路，再扩必须挪件
- 2.4″：显示区更小，方便把近端阻容外移腾扇出环

## 3. 2026-09-05 挪件试做

### 已做
- 外移 15 个器件：`C12–C18, C28, C34–C37, D5, R27, Y1`（径向推出 ≳14.5 mm）
- 扩大 U2 邻域过孔环，邻域内改为 **pad 0.50 / drill 0.30**
- 对过近孔对做分离迭代

### 几何检查
```sh
python3 tools/check_u2_via_pitch.py portable_display_epass.kicad_pcb --radius 26
# RESULT: PASS（0.50 盘下 pairs_below_0.15 = 0）
```

### 重要警告
1. **过孔挪位后原扇出走线端点会悬空**，KiCad 中会有大量飞线；**不能当可投板文件**。
2. 未做完整原生 DRC 放行；`fabrication_released` 仍为 false。
3. 电容外移可能拉长去耦路径，需人工把关键去耦再贴回 U2 近旁（避开孔阵）。
4. 需目视 USB/MIPI 是否被孔阵侵入。

### 文件
- 修改后的 PCB：`portable_display_epass.kicad_pcb`（本分支）
- 相对 `board` 基线的补丁：`reference/u2_0p3_fanout_try.patch`（若整板提交过大可用补丁复查）

## 4. 判定

| 问题 | 判定 |
|------|------|
| 2.4″ + 挪件后 0.3 几何 | **可行（脚本 PASS）** |
| 是否已可投板 | **否**（需重布铜线 + DRC） |
| 询价最小孔 | 在完成重布前，正式 Gerber 仍应按 **0.2** 理解 `board`；本实验分支另论 |
