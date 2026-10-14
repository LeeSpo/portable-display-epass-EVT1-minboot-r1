# FEL 恢复通路修复（fix/preflight-blockers）

状态：静态检查通过（`tools/check_fel_recovery.py` → `static_checks_passed: true`）。**未经实物验证，fabrication 仍未放行。**

## 电路
| 位号 | 值 | 料号 / LCSC | 作用 |
|---|---|---|---|
| R33 | 1k | 0402WGF1001TCE / C11702 | FEL_KEY_N（SW6 / J3.7）→ FEL_N 串联限流 |
| R34 | 10k | 0402WGF1002TCE / C25744 | FEL_N 上拉到 3V3（VCC-PC 域） |

- CPU 引脚：U2.56 = PC1（SPI0-CS0）。依据：V851S-PER2 参考原理图 p8（FEL 键经 R15=0R 接 PC1/pin 56）。我们用 1k 代替 0R：既能防止固件误把 PC1 设成输出时与按键短路，按下时 PC1 仍然低于 0.1V。
- 默认启动选择 11（PC3=1 / PC2=1）保持不变。
- BROM 流程（用户手册图 3-9）：先进行 UART 握手，超时后转入 USB FEL。所以上电后要等到 USB 枚举完成，再松开按键。

## 铜皮（commit e54e0f5）
- R33/R34 旋转 180°，方便走线。
- FEL_N：U2.56 引出过孔 (14.32,28.24) → In1.Cu 0.15 mm 走线 (13.8,27.7)→(6.5,27.7) → 过孔 (6.0,28.2) → F.Cu 接 R33.2 和 R34.2。
  - 最初试过 In2，但它会把 1V8/3V3 铺铜切开，所以改到 In1。In1 是 GND 平面，这里只开了一条很窄的缝，回流影响很小。
- FEL_KEY_N：SW6 (10.55,29.8) → 过孔 (9.4,29.0) → R33.1。
- R34.1 → 3V3 过孔 (7.9,26.75)。

## 使用方法
1. 冷启动前，按住 SW6，或把 J3.7 拉低（夹具用开漏输出，不另加上拉，和 J3.1 共地）。
2. 上电，等 USB FEL 枚举完成后松开。
3. 固件必须把 PC1 保留给 FEL，不能配置成输出或 SPI0 CS。

## 未验证
- BROM 枚举没有实测过（`brom_enumeration_verified: false`）。
