# 2.4″ 真 AOD 显示接入（本分支目标）

> Branch: `feat/display-2p4-aod-rm690b0`（从 `board` 拉出）  
> 与 `feat/u2-via-0p3-fanout-verify` **分开**；本分支不改 U2 0.3 孔实验。  
> `board` 继续推进无屏 minboot；本分支并行接显示。

## 目标面板

- 约 **2.4″ AMOLED**，驱动族：**RM690B0 / ICNA3312**（或同族可 Command Mode + GRAM + AOD 的模组）
- 接口：**MIPI DSI 2-lane**（主机侧通用 2-lane 座 / 自定义 FPC，无转接小板）
- 产品意图：真 **AOD**（模组 GRAM / self-refresh），SoC（V851s）可睡、RISC-V + IMU 待机唤醒

## 本分支要做的事

1. **锁料**：向厂商确认 Command Mode / GRAM / AOD / TE / 复位 / 供电轨（ELVDD/ELVSS 等是否模组内 PMIC）。
2. **原理图**：把显示占位改成真连接——MIPI、TE、RESET、电源、背光/EL（若外置）、I2C/SPI 配置口（若有）。
3. **连接器 + FPC**：按选定模组 pinout 落座与柔板约束；板框仍约 58×110 mm。
4. **PCB 布线**：完成显示区走线；USB/MIPI 阻抗与叠层按嘉立创规则核对。
5. **门控**：本分支合回 / 放行投板前，**不**改 `fabrication_released`；需原生 DRC + 更新 `docs/NEXT_STEPS.md` / release gates。

## 明确不做（本分支）

- 不在本分支做 U2 0.3 mm 过孔扩环重布（见另一 feat 分支）
- 不默认改走 4.4″ SD5207 大屏路径（大屏为备选，另开分支）
- 不把无屏 minboot 的电源/USB 大改推到阻塞显示接入（冲突时先对齐 `board`）

## 验收（初版）

- [ ] 选定具体模组料号 + 数据手册要点进仓库
- [ ] 原理图显示页无占位飞线（或仅剩已标注 TBD 电源焊盘）
- [ ] PCB 显示相关网络已布通；DRC 无新增阻断
- [ ] Tina / 驱动侧：Command Mode + TE 接入点在 `docs/BRINGUP.md` 有条目（可后补固件）

## 和主线关系

- 默认分支 / 无屏样板：`board`
- 本 PR：draft，目标 base = `board`
