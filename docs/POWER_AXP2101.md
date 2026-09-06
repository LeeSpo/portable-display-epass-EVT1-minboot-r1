# 电源选型与纸面审查闭环 · AXP2101（C3036461）

> Branch: `feat/power-axp2101-c3036461`（自 `board`）  
> **设计假设（2026-09-06 Sameat 确认）：** 按全志 V85x 参考板配套 AXP2101 默认轨推进——DCDC1=3.3 V、DCDC3≈0.9 V、DCDC4=**1.5 V**（DRAM）、ALDO1=1.8 V。立创 `C3036461` 按此理解；首板仍建议限流量验，但不阻塞原理图/布局继续。  
> **纸面工作：已完成**  
> **实物：首板冒烟前建议抽测 OTP；不阻塞当前设计推进**  
> `fabrication_released` = **false**（其它门未关前仍不可投板）


## 0. 当前工作假设（已确认）

经确认：**先按全志参考默认做**，不再因「货架 OTP 未实测」卡住电源选型。

| 轨 | 假设默认 | 依据 |
|---|---|---|
| DCDC1 → `3V3` | 3.3 V | V853/V851s PER 电源树 |
| DCDC3 → `CORE_0V93` | ≈0.9 V | 同上（VDD-SYS） |
| DCDC4 → `DRAM_1V5` | **1.5 V** | 同上（VCC-DRAM）；boot 亦常再设 1500 mV |
| ALDO1 → `1V8` | 1.8 V | 参考 / 本板意图 |
| 充电 | 固件再配 0.5–0.8 A | 与 OTP 无关 |

**风险接受：** 若某盘 `C3036461` EFUSE 不是上述值，首板限流可发现；固件仍应显式写 DCDC4=1.5 V。  
**不因此** 将 `fabrication_released` 置 true。

## 1. 选型（已锁定）

| 项 | 决定 |
|---|---|
| 器件 | X-Powers **AXP2101**（默认线性充电；本板 `SW` 未用，与 linear 路径一致） |
| 封装 | QFN-40-EP 5×5 / `Sameat:QFN40` |
| 采购 | 立创 / 嘉立创 SMT **`C3036461`** |
| 电池 | 单节 ≈2000–2500 mAh + NTC（座子，用户不焊接） |
| 充电电流（固件候选） | **0.5–0.8 A** |
| 显示 EL | **屏模组 PMIC**，不挂本芯片高压轨 |

依据：芯智汇《AXP2101 设计指南》V1.0；本仓 `01_power.kicad_sch` / `design/pin_contract.json`。

## 2. 轨映射（已锁定）

| 通道 | 板上网 | 目标 | 电感 |
|---|---|---|---|
| DCDC1 | `3V3` | 3.3 V | L1 1 µH / 2 A |
| DCDC3 | `CORE_0V93` | ≈0.9–0.93 V | L2 1 µH / 2 A |
| DCDC4 | `DRAM_1V5` | **1.5 V** | L3 1 µH / 2 A |
| DCDC2 | 未用 | OFF | — |
| ALDO1 | `1V8` | 1.8 V | — |
| RTCLDO | `RTC_3V3` | RTC 常开 | — |
| VMID | 短至 `VSYS` | 现设计保留 | 旁路不可省 |

## 3. 原理图纸面审查（对照设计指南）

| 检查项 | 指南要求 | 本板状态 | 结论 |
|---|---|---|---|
| DCDC 电感 | 1 µH，Isat>负载×1.3，DCR≤30 mΩ | L1/L2/L3 标称 1 µH/2 A | **纸面 OK**；贴片时核对具体料号饱和电流 |
| 未用 LDO | 输出可悬空、默认关 | ALDO2–4/BLDO/DLDO/CPUSLDO 多为未用 | OK |
| 未用 DCDC2 | VIN 按参考接，LX/FB 悬空 | LX2/FB2 未接网络 | OK |
| BLDOIN | 仅此脚可用 DCDC 作输入；≥4.7 µF | 接 `3V3`；BLDO 未用 | OK（未启用 BLDO） |
| VREF | 1 µF 到地，靠近芯片 | 有 `VREF` 网络与 1 µF 类电容 | OK；Layout 保持靠近 |
| VBUS/VMID 电容 | **不可省** | VSYS/VBUS 有 22 µF 级；VMID=VSYS | OK；投板前目视电容位号 |
| TS / NTC | 建议 10 k NTC；不用则 10 k 对地或关检测 | `BAT_NTC` + 电池座 | **选型时电池座 NTC=10 k** |
| CHGLED | 可接 LED 或悬空 | `CHGLED_N` + CHARGE LED | OK |
| SDA/SCL/IRQ 上拉 | 需上拉 | R3/R4/R5/R6 等 2.2k/4.7k 到 3V3 | OK；IRQ 建议确认≈10 k（现网有 2.2k 级，可接受） |
| PWRON RC | 按键 RC | `PWRON_N` 存在 | 上电前核对接键 RC 是否齐全 |
| USB CC | 5.1 k 下拉 | R1/R2 5.1 k | OK（UFP） |
| 线性充电 | 默认可增加 DCDC5；SW 模式另布 | SW 未用 | 与 C3036461 linear 叙述一致 |
| DCDC4 默认 | 举例常 1.1 V | 目标 1.5 V | **OTP 实测前不算关闭** |

详细电容/电感对照见 `docs/POWER_PASSIVE_MAP.md`。Layout 大电流线宽（VBUS/BAT/VSYS/VIN/LX >150 mil）见 `docs/POWER_LAYOUT_CHECKLIST.md`——**须在 PCB 目视勾选，本文不代替**。

## 4. 仍须实物才能关闭的项

1. **OTP 抽测（建议，不阻塞设计）**— 首板限流量 `DRAM_1V5`；附录可后填  
2. 限流台架温升 / 实际充电电流  
3. 电池电量计 128 参数（寄芯智汇/代理测，或接受简化 SoC 电压估算）  
4. 带屏负载后的 3V3/1V8 余量  
5. 人工在 `release_gates.json` 签字并改 `fabrication_released`

## 5. 附录：OTP 实测（待填）

| 日期 | 批次 | DCDC1 | DCDC3 | DCDC4 | 1V8 | RTC | 结论 | 人 |
|---|---|---|---|---|---|---|---|---|
| | C3036461 | | | | | | 待测 | |

测量步骤见 `docs/BRINGUP.md` §电源分阶段。
