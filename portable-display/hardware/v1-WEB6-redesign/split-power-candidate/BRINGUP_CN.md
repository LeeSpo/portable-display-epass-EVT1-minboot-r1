# 首次上电 / Bring-up 流程（EVT1 split-power candidate）

> 状态：设计文档。Fabrication **NOT released**。

## 0Ω 隔离链接（全部 0402WGF0000TCE，LCSC C17168，JLC basic，≈$0.0011）

| 位号 | PMIC 侧网络 | 负载侧网络 | 位置 / 层 | 隔离的负载 |
|---|---|---|---|---|
| R39 | 3V3_PMIC (L1.2, C4, C5, U1.13/17/21) | 3V3 | (17.6,50.2) B.Cu | 3V3 主干：U10(背光升压)、U8、U2.22/44/47/55、SD、传感器… |
| R38 | 3V3_PMIC | 3V3_B | (27.6,45.7) F.Cu 45° | 北侧支路：Q3.2、U2.5、U2.78、D1.1、C14 |
| R36 | CORE_0V93_PMIC (L2.2, C6, C7, U1.4 FB) | CORE_0V93 | (33.2,54.65) F.Cu | V851S 内核 |
| R37 | DRAM_1V5_PMIC (L3.2, C8, C9, U1.9 FB) | DRAM_1V5 | (30.75,46.0) F.Cu | 片内 DRAM |
| R40 | 1V8_PMIC (U1.18 ALDO1, C10) | 1V8 | (24.6,44.5) F.Cu 90° | U2.37/62/79 等 1V8 负载 |

注意：DCDC 反馈点（U1.4 / U1.9）在 PMIC 侧，链接断开时 PMIC 可空载稳压；链接压降（<50mΩ×电流）在负载侧不被补偿，CORE 在 ~0.5A 时约 −10…−25 mV，可接受，首板实测确认。

默认 **贴装**（量产 BOM 直接焊 0Ω）。首板中 1–2 片由手工拆除全部链接后按下述流程逐路恢复；其他板直接上电。

## 流程（建议使用限流电源，VBAT/VBUS 先限 200 mA）

1. **目检**：U1/U2 方向、J4/J5、二极管极性丝印。
2. **对地电阻（不上电）**：分别量 3V3、3V3_B、CORE_0V93、DRAM_1V5、1V8、VSYS、VBUS 及各 *_PMIC 网络对 GND。任何 <10 Ω（CORE 允许较低但应 >1 Ω）先排查短路。
3. **拆链接上电**：R36–R40 全部开路，接电池/USB，按 PWRON。量 3V3_PMIC≈3.3V、CORE_0V93_PMIC≈0.93V、DRAM_1V5_PMIC≈1.5V、1V8_PMIC≈1.8V、VSYS。核对与 OTP 默认值一致（见 POWER_REVIEW_CN.md / power_requirements.json rail_requirements；VSYS-max OTP 问题仍待 X-Powers 确认）。电压不对 → 不要装链接，先查 OTP/I²C（PMIC_SDA/SCL 可用 I²C 读 0x82/0x84/0x85/0x92）。
4. **逐路恢复**（每步断电焊接，复测电流和电压）：
   1. R39（3V3 主干）→ 电流应 <30 mA（U10 关断，LCD_EN 低）。
   2. R38（3V3_B 北支路）。
   3. R40（1V8）。
   4. R37（DRAM 1.5V）。
   5. R36（CORE 0.93V）→ SoC 开始启动，电流跳升正常；观察 UART / USB FEL。
5. **功能**：FEL（按 FEL 键上电）、USB 枚举、SD、LCD_EN→U10 背光（TPS65631 软启动，无需额外负载开关）。
6. 任何一步电流异常或电压跌落：立即断电，记录网络和电流，不要继续下一步。
