# 电源与关键信号原厂依据复核

复核日期：2026-10-14（Asia/Shanghai），延续 2026-10-09 审查目录。对象为当前 `split-power-candidate` 工作区，PCB SHA-256：`9801b487f879cf5314230d11dbd18dc759a0dfbec91ab028c0c4b6da58afe1ae`。本文件没有修改设计，没有实板测量。来源、页码、计算条件与当前逐脚事实见 [electrical_sources.json](electrical_sources.json)。

## 1. 结论与阻断项

现有电源分配和 USB/FEL/显示引脚映射有资料依据，但“可可靠启动并正常工作”尚不能确认。需要优先关闭：PMIC 批次默认配置与启动时序、常供电电压公差及 I²C 电平、屏幕偏压输入范围、默认关屏及掉电时序。ERC/DRC 对这些模拟边界和出厂配置没有证明能力。

| 编号 | 当前事实、规格比较与影响 | 关闭条件 |
|---|---|---|
| E01 | `power_requirements.json` 的出厂配置标记为未核实。U1 使用 DCDC1→3V3、DCDC3→CORE_0V93、DCDC4→DRAM_1V5、ALDO1→1V8；DCDC2/5 未装外部电感。寄存器写入发生在主控启动后，不能代替首次冷启动供电保证。 | 供应商按采购批次确认电压、默认使能、未用通道关闭、PWRON 模式及启动顺序，并实测电池/USB/混合供电冷启动。依据：[AXP2101 V1.4](https://wiki.lilygo.cc/datasheet/AXP2101_Datasheet_V1.4_en.pdf#page=22)，第22、50–54页。 |
| E02 | U1.28→RTC_3V3→U4.9/VDD、U4.10/VDDIO。按目标3.3V及 RTCLDO ±10%，包络2.97–3.63V；高角比 LIS2DW12 的 VDD 工作上限3.6V高30mV。它仍低于绝对最大额定值，不能据此断言损坏，但当前公差保证不闭合。 | 以受控供电规格或改动关闭全温/负载公差，覆盖全部常供电负载；不能只测一颗典型芯片。依据：[AXP 第14页](https://wiki.lilygo.cc/datasheet/AXP2101_Datasheet_V1.4_en.pdf#page=14)、[ST 第7、12页](https://www.st.com/resource/en/datasheet/lis2dw12.pdf#page=7)。 |
| E03 | R15/R16为4.7k，上拉到主3V3，U4的VDDIO却来自常供电轨。若 DCDC1 按 PWM 精度+3%为3.399V，而RTCLDO为低角2.97V，空闲总线可能超过 ST 控制脚上限 `VDDIO+0.3V`：3.399−(2.97+0.3)=0.129V。4.7k不能直接等同于已取得允许注入电流。 | 给出两条电源的相关性/限制保证，或完成供电/隔离修复；复测总线上电、掉电、关机和重启。依据：[AXP 第13–14页](https://wiki.lilygo.cc/datasheet/AXP2101_Datasheet_V1.4_en.pdf#page=13)、[ST 第12页](https://www.st.com/resource/en/datasheet/lis2dw12.pdf#page=12)。这是允许独立极限同时出现的计算，不是已测129mV过压。 |
| E04 | U10.11/AVIN、.12/PVIN直连VSYS。TPS65631推荐输入2.9–4.5V；电池低压、插USB、无电池、充电、满电与瞬态的VSYS包络未给出。AXP REG14通用POR为4.7V **DPM设定**，不是VSYS固定输出实测值。 | 实测全部工况的VSYS与U10输入，保证2.9–4.5V；若不能保证则另审电源架构。依据：[TI 第4页](https://www.ti.com/lit/ds/symlink/tps65631.pdf#page=4)、[AXP 第18、33页](https://wiki.lilygo.cc/datasheet/AXP2101_Datasheet_V1.4_en.pdf#page=33)。 |
| E05 | LCD_EN连接U2.4/PD21、U8.3/ON和U10.7/CTRL；没有外部下拉，R31为DNP。TPS65631内部下拉150–860kΩ、保证低电平≤0.4V；V851允许高阻输出漏电±10µA。最弱下拉在0.4V仅吸收约0.465µA，无法覆盖允许的正漏电。实际电压受芯片非线性限制，不能用10µA×860k直接宣称会出现8.6V。 | 增加经漏电、上电默认内部拉和驱动能力核算的确定关断方案，测GPIO尚未初始化和主控掉电时的CTRL/ON、VCI及偏压。依据：[TI 第5–6页](https://www.ti.com/lit/ds/symlink/tps65631.pdf#page=5)、[全志表2-7，PDF42/印刷28页](https://bbs.aw-ol.com/assets/uploads/files/1664112156052-c55b9458-9847-4731-873e-c98d352589ea-v851s-amp-v851se_datasheet_v0.1.pdf#page=42)。 |
| E06 | U8.5/QOD开路，是厂家允许的用法，但关闭后没有该开关提供的快速输出放电。不能由LCD_EN拉低推断VCI已及时归零。U8与U10共用LCD_EN，还须检查VCI与偏压的实际先后顺序。 | 取得屏厂可执行的电源时序要求，示波器验证开/关屏、异常掉电、快速重启的VCI/VDDIO/ELVDD/ELVSS/RESX；必要时审放电/时序电路。依据：[TPS22918 第13页8.3.2](https://www.ti.com/lit/ds/symlink/tps22918.pdf#page=13)。 |
| E07 | J2.2/BAT_NTC连U1.31/TS。最终电池的NTC曲线、充电电压/电流、温度限值和电池允许参数未绑定；仅有三针连接不构成充电验收。AXP手册通用输入限流POR为1.5A，也不能证明USB主机或电源已授予相同电流。 | 绑定电池规格、批次PMIC配置和USB输入电流策略，验证NTC开/短路、温度边界、无电池及充电温升。依据：[AXP 第25–26、34页](https://wiki.lilygo.cc/datasheet/AXP2101_Datasheet_V1.4_en.pdf#page=25)。 |

## 2. 有依据的连接与电压

以下数值包络按目标电压、手册指定精度条件及稳态计算；没有包含PCB压降、纹波、瞬态、启动前OTP未知状态。

| 电源/接口 | 当前连接与复核结果 |
|---|---|
| 核心/DRAM/主IO | 0.93V±30mV→0.90–0.96V；1.5V±3%→1.455–1.545V；3.3V±3%→3.201–3.399V，分别在全志列出的0.81–1.0V、1.425–1.575V、2.97–3.63V范围。需满足手册精度的模式条件和实测动态要求。 |
| 外部1V8 | ALDO1目标1.8V，在其精度测试条件下±3%→1.746–1.854V；覆盖VDD18-DRAM所需1.7–1.95V及PA/MDSI范围。内部LDOA输出SOC_LDO_1V8与外部1V8分开，没有把两个输出硬并。 |
| 屏幕RESET/TE | U2.66/PA8→J4.16/RESX，R32=10k下拉；J4.15/TE→U2.65/PA9；U2.62/PA供电与R29=0R后的J4.11/VDDIO共享1V8。共享电源条件下，全志VOH/VOL与面板0.8/0.2×VDDIO阈值有静态余量。须同步固件PA8/PA9配置。 |
| 面板偏压 | TPS65631默认+4.6V/−4.0V均在面板ELVDD 2.0–6.0V、ELVSS −4.7至−0.4V的DC范围内；不能把面板典型±3.6V误当绝对工作上限。该DC比较不承诺当前偏压下的亮度、寿命、功耗或上/下电时序。 |
| MIPI/FPC | J4.31/IM1、.32/IM0为GND，对应MIPI；数据J4.35/D0P→U2.81、.36/D0N→U2.80，时钟J4.39/CLKP→U2.85、.40/CLKN→U2.84，极性一致。原厂屏资料给出456MHz MIPI参考与18.5MHz DCLK；铜连通/长度报告不能替代阻抗、眼图及显示测试。 |

电源与GPIO阈值依据：[全志V851S/V851SE表2-6/2-7，PDF39–42页](https://bbs.aw-ol.com/assets/uploads/files/1664112156052-c55b9458-9847-4731-873e-c98d352589ea-v851s-amp-v851se_datasheet_v0.1.pdf#page=39)；屏幕DC与接口以仓库原始屏厂PDF为准，PDF22/印刷23页与PDF13–14/印刷14–15页。电源公差依据：[AXP第13–14页](https://wiki.lilygo.cc/datasheet/AXP2101_Datasheet_V1.4_en.pdf#page=13)。

## 3. 启动、默认状态和固件条件

- **FEL依据成立。** [全志V851S-PER2参考原理图第8页](https://bbs.aw-ol.com/assets/uploads/files/1663052776026-7acd717f-af1c-47d5-8177-89b930ec2085-v851s_per2_qfn88_axp2102_v12_20220705.pdf#page=8)将FEL按键通过R15=0R接SPI0-CS0，CPU端为PC1/56脚。本板PCB的U2.56/R33/R34/SW6恢复电路可据此审查，但当前原理图网表仍将U2.56列为未接，须先关闭原理图/PCB差异。
- **USB恢复可能有等待。** [BROM图3-9，PDF172/印刷158页](https://bbs.aw-ol.com/assets/uploads/files/1664112156052-c55b9458-9847-4731-873e-c98d352589ea-v851s-amp-v851se_datasheet_v0.1.pdf#page=172)画出UART升级握手超时后转USB升级。不能凭上电后短暂未枚举直接判USB坏；资料未给这里的确定超时时长。
- **SA0开路不能报成无任何偏置。** [ST第4–5、20页](https://www.st.com/resource/en/datasheet/lis2dw12.pdf#page=4)说明SDO/SA0有内部上拉；U4.2/CS已接VDDIO。因此I²C模式和默认高地址有依据，固件仍须实测地址/WHO_AM_I、噪声和低功耗配置。
- **关机I²C不等于必然倒灌。** 当前上拉来自已关断的主3V3，U4的SCL/SDA为开放漏极接口。没有证据可断言它们关机时主动向主控输出常供电高电平。应测掉电波形、残压、泄漏、总线恢复和唤醒后访问；若将上拉直接改常供电，则要重新审主控掉电容忍。
- **唤醒需要初始化。** U4的INT默认推挽输出低；当前唤醒检查器采用低有效、锁存中断和禁止重复边沿的工作策略。这是固件装配后的必要配置，不能由默认寄存器状态推断可靠周期唤醒。
- **屏幕初始化已有参数。** 屏厂原始PDF17/印刷18页：RESX低脉宽至少30µs，复位完成时间分别标20ms（sleep-in）/120ms（sleep-out）；PDF21/印刷22页初始化给出sleep-out命令0x11后等待120ms再0x29。上电/掉电电源图与AOD配置仍须屏厂澄清并实测。

## 4. 首板需留的电气证据

限流供电并记录VBUS/VBAT/VSYS、主电源、RTCLDO和内部LDOA完整波形；先确认电压与时序，再检查24MHz/UART、USB两种插向及FEL、TF、I²C与唤醒，最后连接屏幕测试电源时序、复位、MIPI和显示。各项需记录具体器件批次、固件版本、仪器、工况、测点和波形；本审查的静态结果不能替代这些证据。
