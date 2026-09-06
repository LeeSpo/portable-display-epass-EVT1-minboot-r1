# 电源选型锁定 · AXP2101（C3036461）

> Branch: `feat/power-axp2101-c3036461`（自 `board`）  
> 状态：**料号与轨映射已锁定**；OTP 默认电压仍须到料实测后才能关闭 `pmic_variant` 门。  
> `fabrication_released` 保持 **false**。

## 1. 选型结论

| 项 | 决定 |
|---|---|
| 器件 | **X-Powers AXP2101**（单节 NVDC PMU，线性充电路径） |
| 封装 | **QFN-40-EP (5×5)**，与原理图 `Sameat:QFN40` / U1 一致 |
| 采购料号 | **立创 / 嘉立创 SMT：`C3036461`**（MPN 标为 AXP2101） |
| 产品约束 | 挂牌、USB-C、约 2000–2500 mAh 单节、最终带 2.4″ AOD；OLED EL 轨走屏模组 PMIC，不挂本 PMIC 高压 |

**不更换** 电源芯片家族（避免重画电源域）。公开货架料号通常**不印刷具体 OTP 版本号**，因此「可买」≠「默认轨已匹配 V851s」。

## 2. 与本板网络映射（设计意图）

来源：`design/pin_contract.json` U1。

| AXP 通道 | 引脚 | 板上网名 | 目标电压 | 备注 |
|---|---|---|---|---|
| DCDC3 | FB3 / LX3 | `CORE_0V93` | ≈ **0.90–0.93 V** | V851s 核电 |
| DCDC4 | FB4 / LX4 | `DRAM_1V5` | **1.5 V** | DDR；公开手册举例常见默认 **1.1 V** → **必须实测** |
| DCDC1 | FB1 / LX1 | `3V3` | **3.3 V** | IO / 外设 |
| DCDC2 | LX2 / FB2 | （未用） | OFF | 保持关闭 |
| ALDO1 | ALDO1 | `1V8` | **1.8 V** | |
| RTCLDO | VRTC | `RTC_3V3` | RTC 常开轨（按最终 RTC 需求核对） | |
| — | VMID | 已短至 `VSYS` | — | 现设计保留；审签时书面确认 |
| — | BAT / TS | `VBAT` / `BAT_NTC` | 单节 + NTC | |
| — | VBUS | `VBUS` | USB 输入 | |
| — | SDA/SCK/IRQ | `PMIC_SDA` / `PMIC_SCL` / `PMIC_IRQ_N` | Tina / 设备树 | |

未用 LDO（ALDO2–4、BLDO1–2、DLDO、CPUSLDO、DCDC2 等）默认关闭，输出可悬空（按 X-Powers 设计指南）。

## 3. 充电与电池（候选参数）

| 项 | 候选值 | 说明 |
|---|---|---|
| 电池 | 单节 Li-ion/Li-Po ≈ 2000–2500 mAh | 插拔电池座，用户不焊接 |
| 充电电流（固件） | **0.5–0.8 A** 起步 | 挂牌散热差，勿默认拉满 1–1.5 A |
| NTC | 接 `BAT_NTC` | 冷热停充按手册使能 |
| 首板上电 | 限流台架，先无电池 / 再接电池 | 见 `docs/BRINGUP.md`（仍待填具体限流值） |

`power_thermal_battery` 门在完成环路/温升审查前保持 open。

## 4. OTP / 上电顺序验收（关闭 pmic_variant 前必做）

公开数据手册举例常见默认（**仅供对照，以到料实测为准**）：

- DCDC1 ≈ 3.3 V  
- DCDC2 / DCDC3 ≈ 0.9 V  
- DCDC4 ≈ **1.1 V（与本板 1.5 V DRAM 冲突风险）**

**验收步骤：**

1. 嘉立创贴片或散装到料后，记录批次 / 盘号。  
2. 不上主 SoC 负载或限流条件下上电，用万用表 +（可选）I2C 读默认寄存器，记录各 DCDC/LDO 默认电压与使能。  
3. 判定：  
   - **通过**：DCDC3≈0.9 V、DCDC4≈1.5 V、DCDC1=3.3 V，或已确认 U-Boot 最早阶段可安全改压且 DRAM 无过压风险。  
   - **不通过**：联系代理确认 V85x / 1.5 V DRAM OTP 批次，或调整 bring-up（禁止在错误轨上挂满负荷 DRAM）。  
4. 将测量表贴进本文件「附录：OTP 实测」并更新 `design/release_gates.json` 的 `pmic_variant.evidence`。

固件侧：无论 OTP 是否理想，Tina / U-Boot / 设备树仍须**显式配置**各轨电压与充电电流，不依赖默契。

## 5. 与显示的关系

最终产品**必须带屏**。电源本分支只锁定主机 PMIC；2.4″ 真 AOD 在 `feat/display-2p4-aod-rm690b0`。  
屏逻辑电可来自 `3V3` / `1V8`（按模组手册）；**ELVDD/ELVSS 等优先模组内 PMIC**。

## 6. 本分支交付 / 非目标

**已做：** 料号锁定、轨映射、充电候选、OTP 验收标准、门控证据指针。  
**未做：** 改 PCB 铜皮、改封装尺寸、OTP 实测、关闭 `fabrication_released`。

## 附录：OTP 实测（待填）

| 日期 | 批次 | DCDC1 | DCDC2 | DCDC3 | DCDC4 | RTCLDO | 结论 | 记录人 |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | 待测 | |
