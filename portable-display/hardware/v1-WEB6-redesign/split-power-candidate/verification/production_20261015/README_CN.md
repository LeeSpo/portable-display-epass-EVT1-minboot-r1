# JLC 生产包（2026-10-15）——**还没有放行生产**

- **来源：** 提交 `d49a636`（fix/preflight-blockers）。主 PCB 文件 SHA-256：`94dfe7223654ee6a35d66aa2d591a83110220de74a82acc37a12f044bfb41f0e`。这里的全部文件都是从这一个提交导出的。
- **当前状态：**
  - `fabrication_released = false`。
  - 还没关闭的阻塞项见 ../../OPEN_ISSUES_CN.md：电源 OTP 冷启动配置还没确认，屏幕的机械和 FPC 也还没确认。
  - 这个包只用来报价和 JLC 预览检查。
- **文件：**
  - `gerber_jlc.zip` / `gerber/`：
    - F.Cu、In1.Cu、In2.Cu、B.Cu 四层铜
    - F/B 阻焊、F/B 钢网、F/B 丝印（已减去阻焊开窗）
    - Edge.Cuts
    - PTH.drl、NPTH.drl（Excellon，单位 mm），加上钻孔图
    - gbrjob（里面有叠层信息）
  - `BOM_JLC.csv`：54 行，128 颗。每一颗都有 LCSC 料号。
  - `CPL_JLC.csv`：128 颗，双面（B 面 11 颗）。
  - `checks/`：导出时的检查结果，DRC、ERC、未连接、一致性全部为 0，power_contract/fel_recovery/usb_routing/wake_domain 全部通过。
- **不在 BOM/CPL 里的器件：**
  - R31：DNP。
  - J3：调试弹针测试焊盘，不贴装。
  - H1–H4：安装孔。
- **R36–R40（0 Ω 隔离电阻）：** 在 BOM 里照常贴装。按 ../../BRINGUP_CN.md，调试时可以拆掉做分段上电。
- **PCB 下单参数**（详见 ../../ORDERING_GUIDE_CN.md）：
  - 4 层，1.0 mm，阻抗控制叠层 **JLC04101H-3313**，ENIG。
  - 过孔 0.60/0.30 mm，**全部做 Epoxy Filled & Capped（POFV）**。
  - 阻抗备注：USB 90 Ω 差分 w0.127/s0.14，MIPI 100 Ω 差分 w0.10/s0.15，都在 L1 层、以 L2 为参考。
  - 双面贴片，选标准型 PCBA（U1/U2 是 QFN，要做 X-Ray）。
- **JLC 预览时要检查：** 按 ORDERING_GUIDE 的方向检查表，逐个确认 1 脚和极性。CPL 里的旋转角是 KiCad 原值，JLC 预览时可能需要手动修正个别器件的方向。

- 这一版替换了 aa48459 导出的旧包，新增了 B 面 CORE 去耦电容 C56/C58/C61。
