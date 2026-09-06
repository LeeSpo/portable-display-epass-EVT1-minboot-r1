# 电源后续（摘自选型锁定）

详见 [POWER_AXP2101.md](POWER_AXP2101.md)。

1. 按 `C3036461` 备料 / 嘉立创 SMT。  
2. 到料填 OTP 实测表；通过后更新 `design/release_gates.json` → `pmic_variant`。  
3. 与 `feat/display-2p4-aod-rm690b0` 并行锁屏；投板以**带屏**版为目标。  
4. 完成去耦环路、载流、电池保护审查后关闭 `power_thermal_battery`。
