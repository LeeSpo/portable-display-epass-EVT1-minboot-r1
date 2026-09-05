# Portable Display ePass - EVT1-minboot-r1

**工程修复候选版。不可直接投板、采购贴片或上电。**

本版以用户上传 ZIP 的根目录工作区为基础，而不是旧 `main` 或旧三环扇出基线。基准工程核心文件此前对应内层 Git 的 `Save_project_2 / 450134c`。原始 ZIP 未修改；导入校验值见 `reference/import_manifest.json`。

## 本版完成的修改

修正 U9 旋转变换造成的 12 段走线及 6 个过孔网络归属错误；修正 TPS22918 的六脚封装和 VOUT=6、CT=4、QOD=5 引脚定义；重新布置 U2 的非显示扇出，54 个目标引脚均在静态几何模型中连接到对应过孔。

统一当前原理图、PCB、生成器和本地库的引脚数据，修复 24 个重复铜线 UUID，补齐原理图层级路径，纠正旋转封装的焊盘角度。C34/C37 左移 0.5 mm 以留出扇出空间，其余已知电容位置漂移按当前 PCB 同步。

验证流程默认不修改设计，不再自动覆盖 PCB、忽略未连网络或输出 Gerber。贴片坐标预览从实际 PCB 导出，而不是生成器中的旧坐标。旧制造输出封存于 `reference/legacy_outputs_DO_NOT_FABRICATE.zip`。

## 状态必须分开理解

| 项目 | 当前状态 |
|---|---|
| 结构/引脚/所覆盖的几何检查 | 已执行，报告在 verification/static_report.json |
| 单元与集成测试 | 已执行，见 verification/unit_tests.log |
| 原生 KiCad ERC / DRC / 覆铜重填 / 原理图一致性 | 当前环境缺少 KiCad 引擎，未执行 |
| USB、NAND、SD、电源等主干完整布线 | 尚未完成 |
| 屏幕型号与显示区域 | 未定版，保留占位电路 |
| 投板与实物上电 | 未放行，未验证 |

**54/54 仅表示引脚引出到过孔，不表示 54 个网络已完成布线，更不表示板子可启动。**
静态几何检查忽略覆铜连接、热焊盘、阻抗、载流、阻焊、丝印和可制造性；其通过不能替代 KiCad DRC。

## 打开工程

使用 KiCad 9 或 10 打开 `portable_display_epass.kicad_pro`。符号和封装仅引用 `${KIPRJMOD}` 中的本地库，不依赖原作者的个人库路径。第三方生成的文件尚需在原生 KiCad 中打开检查。

## 运行检查

在工程根目录运行：

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/verify_evt1.py --static
```

上面的依赖安装需要网络。`--static` 只运行明确列出的静态检查，永远不会放行制造。

安装好 KiCad 后运行原生检查：

```sh
python3 tools/verify_evt1.py
```

KiCad 9 的覆铜重填使用带 `pcbnew` 的 Python；可显式指定：

```sh
python3 tools/verify_evt1.py --kicad-python /path/to/kicad/python
```

KiCad 10 若支持 `--refill-zones --save-board`，脚本自动采用该功能。整个原生检查在独立 `checked_project` 副本中进行，源 PCB 不被重写。原生路径已编写，但本次环境无法端到端测试，首次运行需要核对日志。

`--release` 会取消显示未连豁免并检查全部人工审签项，但仍不自动导出制造文件。当前审签项全部保持 open，不能靠静态通过绕过。

## 输出与文件职责

- `design/pin_contract.json`：当前设计意图的引脚约定，不等于完成数据手册审签。
- `design/release_gates.json`：必须完成的审查与放行条件。
- `verification/`：本次实际测试、变更记录、坐标和物料预览、待布线统计。
- `docs/`：本版交付说明、验证方法和下一阶段工作。
- `reference/`：历史资料，只读对照，不作为制造输入。

`python3 tools/generate_evt1.py` 默认不写入任何文件；仅显式使用 `--write-schematics` 才重建原理图和本地库，且不重建 PCB。旧 `EVT1_REBUILD_BOARD` 路径已禁用。

## 当前最重要的外部输入

具体屏幕模组的完整型号与数据手册、实际采购的 AXP2101 变体/OTP 默认配置、板厂四层叠层。没有这些信息，不能把显示供电、PMIC 默认电压和高速阻抗当作已确认条件。


---

# EVT1-minboot-r1

基于上传根目录工作区；不是回退到旧 main。所有改变均为工程候选，原生与实物验证未通过。

- 修复 PCB y-down 坐标系的旋转方向，以及旋转封装中的焊盘绝对角度。
- 按独立焊盘的物理连通链修正 U9 的 12 段走线、6 个过孔网络归属。
- U8 改为六脚 TPS22918，修正 CT/QOD/VOUT，原理图/PCB/库/引脚约定同步。
- 以单圈分散候选扇出替换 U2 原有 44 个非显示扇出，形成 54 个同网过孔连接。
- C34/C37 向左移动 0.5 mm；源生成器与实际 PCB 的其他电容位置同步。
- 修复残留 24 个重复铜线 UUID；路径补齐根原理图 UUID，补充层级实例记录。
- 清除过期覆铜填充缓存；辅助坐标原点设为 `(0,110)`，并明确坐标预览含义。
- 工程约束中最小铜间距设为 0.09 mm；若干连接/孔间距/一致性问题提升为 error，未降低规则绕过检查。
- 增加固定引脚约定、静态检查、原生验证隔离快照、哈希追踪、严格报表校验和人工发布门槛。
- 贴片坐标改从 PCB 导出，旧制造文件归档隔离。工程没有新的可投板 Gerber。
- 生成器不再默认写工程；整板重生成及旧坐标导出入口禁用。
- 子原理图使用 A2 纸张以容纳已有电路块；脚本标识如实标为第三方生成。
- 原文档与屏幕讨论移入 reference/original_notes，只作历史对照。


---

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

USB / NAND / SD / PMIC 通信 / 电源等主干尚未完整布线。按忽略覆铜的保守几何统计，仍有多个独立焊盘组的网络见 `verification/routing_backlog.csv`。这不是 KiCad 飞线统计，尤其地和电源平面可能在原生重填后合并。

器件通用封装、阻焊与锡膏、安装孔和壳体、走线载流、USB/MIPI 回流与阻抗、PMIC 供电和充电、按键/唤醒时序、固件及启动方案，都尚不能视为审签完成。

## 本次使用的原始资料

- TI TPS22918 数据手册 Rev C，第 3 页管脚图和功能表：https://www.ti.com/lit/ds/symlink/tps22918.pdf
- ST USBLC6-2 数据手册，第一页管脚图：https://www.st.com/resource/en/datasheet/usblc6-2.pdf
- KiCad 层级实例与生成器标识规范：https://dev-docs.kicad.org/en/file-formats/sexpr-schematic/
- KiCad PCB 格式规范：https://dev-docs.kicad.org/en/file-formats/sexpr-pcb/
- KiCad 9 CLI 文档：https://docs.kicad.org/9.0/en/cli/cli.html

资料用于上述限定的修复，不代表已完成所有器件的全量审查。


---

# 验证范围和拒绝误放行

## 静态检查覆盖

解析工程中的 KiCad S-expression，不执行其中内容。核对 111 个电气器件及 452 个逻辑引脚在设计约定、生成器、原理图符号/标签/NC 标记、PCB 焊盘之间的一致性；另有四个安装孔封装。核对本地库路径、层级实例、PCB 到原理图路径、UUID、位置和旋转。

通过多边形近似检查铜皮对象：最小异网铜间距 0.09 mm、孔到异网铜 0.25 mm、孔到孔 0.25 mm；检查铜线标签是否与其几何接触的焊盘网络相符。通过几何连通分组统计 U2 引脚到同网过孔的连通。圆弧边界采用离散多边形，因此这是近似检查，不是 KiCad DRC。

**不覆盖：**覆铜填充和热焊盘连接、完整 ERC、完整设计规则、自定义焊盘、铜弧、盲埋孔、阻焊/丝印/庭院/铜到板边、阻抗/时序/载流、器件电气正确性和实体制造。遇到静态算法不支持的图形，流程应阻断而不是假定通过。

## 原生流程

每次运行生成唯一目录，把当前输入复制到独立 `checked_project`。原生引擎重填覆铜，再导出网表、ERC、DRC，启用 schematic parity 和全部严重级别。所有输入与输出记录 SHA-256，原始输入不得在检查过程中变化。

只允许非显示阶段明确同一显示网络的未连接项豁免。无法识别的端点、不同网络混杂、缺失 JSON 数组、空文件、缺失原理图器件、重复引脚、任意未处理警告与错误均阻断。全板发布检查不接受显示豁免。

当前环境未提供 `kicad-cli` 或 `pcbnew`。本次记录的原生检查尝试应明确失败，不得解读为已运行并通过。原生自动化路径尚未在本环境完成端到端实测。

## 可重复性

测试不会覆盖 PCB，生成器默认空操作，旧整板重生成和旧 BOM/CPL 导出路径已禁用。`apply_r1_migration.py` 是仅接受原始 PCB SHA-256 的一次性迁移程序；不能把它用于已经继续编辑过的 PCB。它的记录在 `verification/migration.json`。

坐标预览以 PCB 辅助原点 `(0,110)` 为底部原点，X 保持向右，Y=`110-PCB_Y`，角度保留 KiCad 约定。尚未应用贴片厂的送料/零度角修正，因此文件名明确为 PREVIEW_NOT_FOR_ASSEMBLY。


---

# 下一阶段完成顺序

## A. 把设计输入定下来

取得具体屏幕模组数据手册，确认当前 58 x 110 mm 板形是否容纳模块、FPC 弯折与外壳。取得实际采购 AXP2101 的配置和参考电路，核对所有电源、VMID/VSYS 和上电顺序。对 U1/U2/连接器和其他 IC 的针脚与封装逐个审签。

## B. 在原生 KiCad 中建立可信检查基线

打开全部四个子原理图和 PCB，核对本次第三方写入文件。运行 `python3 tools/verify_evt1.py`，先解决读取失败、错误、所有警告与一致性问题，不通过更改严重程度、删除报告或扩大豁免绕过。

## C. 完成非显示最小系统

先安排 PMIC、电感、电容的电源和回流短环路，再处理 SoC 去耦、时钟、复位及 PMIC 通信，继而完成 UART / USB 启动路径。保留完整地参考，不能为走线便利随意切割回流。每完成一组就重填覆铜并运行原生检查。

在此基础上完成 NAND / SD 以及传感器、按键、唤醒。高速走线的线宽和间距根据板厂叠层计算，不能把本版通用最小线宽当作阻抗要求。`routing_backlog.csv` 仅作发现未连接网络的辅助清单。

## D. 显示定版与整板关闭问题

按最终屏幕复核供电、FPC 针脚、DSI 极性和时序、背光驱动；完成布局与布线，再取消显示未连豁免。对全板生产规则、装配、可测试性、保护和机械结构复核。

## E. 发布制造输入与实物验证

所有 `release_gates.json` 项目有明确审签人与证据后，检查同一版本的全量原生报告；再由最终 PCB 生成并复核制造包。首板验证按已批准的上电计划逐步执行。完成此阶段前，不应命名为量产版或声称已经可用。


## Machine-readable result snapshot

```json
{
  "revision": "EVT1-minboot-r1",
  "native_kicad_executed": false,
  "fabrication_released": false,
  "unit_tests_passed": 44,
  "counts": {
    "footprints": 115,
    "schematic_components": 111,
    "pads": 456,
    "tracks": 262,
    "vias": 149,
    "u2_required_fanouts": 54,
    "u2_fanouts_connected_to_via": 54,
    "geometric_issues": 0,
    "copper_net_label_conflicts": 0,
    "multi_net_physical_components": 0
  },
  "u9_copper_objects_corrected": 18,
  "duplicate_uuids_repaired": 24,
  "non_display_nets_with_multiple_pad_groups_excluding_zones": 68,
  "latest_native_attempt": {
    "run": "native-20260905T053502Z-50099d",
    "mode": "NATIVE",
    "native_kicad_executed": false,
    "fabrication_released": false,
    "verification_passed": false,
    "problems": [
      "RuntimeError: kicad-cli is unavailable; native ERC/DRC were NOT executed"
    ]
  }
}
```
