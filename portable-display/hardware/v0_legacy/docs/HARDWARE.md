> 2026-09-05 更新：非显示网络布线与原生检查已完成。本文中“主干尚未完整布线”描述属于历史状态；当前状态见 `MINBOOT_ROUTING.md`。器件电气、阻抗、载流及实物审查仍待完成。

# EVT1-minboot-r1 硬件状态

## 本次实际修复

U9 的错误来源是坐标变换：PCB 文件以向下为正 Y，而原生成器使用了另一种旋转约定。现以焊盘逻辑网络和实际几何连通链为依据修正 12 段走线、6 个过孔，并统一旋转封装的焊盘角度。不是简单照搬历史文件。

U8 / TPS22918DBVR 原来误用五脚封装。已按 TI 数据手册第 3 页改成六脚：1 VIN、2 GND、3 ON、4 CT、5 QOD、6 VOUT。CT/QOD 暂按原意图不连接；ON 的确定默认电平、VIN 旁路和最终显示负载仍需审查，不能把这次引脚修复理解为整段显示供电设计完成。

U2 非显示扇出采用 0.40/0.20 mm 过孔、0.09 mm 走线、先直出 0.60 mm 再分散引出的候选几何。半径方向按焊盘局部坐标 1.65 倍放大，54 个目标引脚全部连到本网络过孔。邻近 C34/C37 左移 0.5 mm。该候选仍需原生 KiCad 和板厂约束复核。

U1 的第 36 脚名称恢复为 VMID，保留现有 VSYS 网络，没有擅自改动此处应用电路。具体 AXP2101 版本的 VMID/VSYS 接法、OTP 默认输出和时序需要可靠资料确认。

## 保留但未确认的设计意图

板形 58 x 110 mm、四铜层，以及原有电源网络名称均保留。网络名 CORE_0V93 / DRAM_1V5 等只是设计意图，不能证明实际采购 PMIC 上电默认值正确。此版本没有完成所有芯片管脚、封装尺寸、热焊盘和电源设计的资料审查。

`J4` 仍为原始 TFT 的 20-pin 占位接口；不能用屏幕尺寸或驱动芯片名推断任何其他模组的接法。显示控制器、背光和接口必须在具体模组选定后一起复核。

## 仍未完成

非显示最小系统已开始在现有 PCB 上布线（电源缝合过孔、VSYS/VBUS 局部覆铜、部分 UART/时钟）。原理图已改为只从 TF 启动：删除 SPI NAND 岛，PC2/PC3 为 `BOOT0`/`BOOT1`。WEB6 38×64 布局候选同步删件；本目录 58×110 PCB 仍是带 NAND 的旧快照。忽略覆铜的焊盘组统计见 `verification/minboot_route_report.json`；原生未连项以最新 `verification/native-*` 为准。

器件通用封装、阻焊与锡膏、安装孔和壳体、走线载流、USB/MIPI 回流与阻抗、PMIC 供电和充电、按键/唤醒时序、固件及启动方案，都尚不能视为审签完成。

## 本次使用的原始资料

- TI TPS22918 数据手册 Rev C，第 3 页管脚图和功能表：https://www.ti.com/lit/ds/symlink/tps22918.pdf
- ST USBLC6-2 数据手册，第一页管脚图：https://www.st.com/resource/en/datasheet/usblc6-2.pdf
- KiCad 层级实例与生成器标识规范：https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/
- KiCad PCB 格式规范：https://dev-docs.kicad.org/en/file-formats/sexpr-pcb/
- KiCad 9 CLI 文档：https://docs.kicad.org/9.0/en/cli/cli.html

资料用于上述限定的修复，不代表已完成所有器件的全量审查。
