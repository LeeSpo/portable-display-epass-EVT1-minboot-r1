# Portable Display ePass - EVT1-minboot-r1

**工程修复候选版。不可直接投板、采购贴片或上电。**

本版以用户上传 ZIP 的根目录工作区为基础，而不是旧 `main` 或旧三环扇出基线。基准工程核心文件此前对应内层 Git 的 `Save_project_2 / 450134c`。原始 ZIP 未修改；导入校验值见 `reference/import_manifest.json`。

## 本版完成的修改

2026-09-05：补齐非显示最小系统布线，清理悬空铜线，USB 主干改为同通道并行走线；原生检查通过。详细范围与未完成的制造/实物审查见 [最小系统布线报告](docs/MINBOOT_ROUTING.md)。

修正 U9 旋转变换造成的 12 段走线及 6 个过孔网络归属错误；修正 TPS22918 的六脚封装和 VOUT=6、CT=4、QOD=5 引脚定义；重新布置 U2 的非显示扇出，54 个目标引脚均在静态几何模型中连接到对应过孔。

统一当前原理图、PCB、生成器和本地库的引脚数据，修复 24 个重复铜线 UUID，补齐原理图层级路径，纠正旋转封装的焊盘角度。C34/C37 左移 0.5 mm 以留出扇出空间，其余已知电容位置漂移按当前 PCB 同步。

验证流程默认不修改设计，不再自动覆盖 PCB、忽略未连网络或输出 Gerber。贴片坐标预览从实际 PCB 导出，而不是生成器中的旧坐标。旧制造输出封存于 `reference/legacy_outputs_DO_NOT_FABRICATE.zip`。

## 状态必须分开理解

| 项目 | 当前状态 |
|---|---|
| 结构/引脚/所覆盖的几何检查 | 已执行，报告在 verification/static_report.json |
| 单元与集成测试 | 已执行，见 verification/unit_tests.log |
| 原生 KiCad ERC / DRC / 覆铜重填 / 原理图一致性 | 已在本机 KiCad 10.0.6 执行；非显示最小系统检查通过，显示仍有 16 项未连豁免 |
| USB、NAND、SD、电源等主干完整布线 | 非显示网络全部连通；当前 ERC / DRC / 原理图一致性无未解决项，阻抗与载流审签仍未完成 |
| 屏幕型号与显示区域 | 未定版，保留占位电路 |
| 投板与实物上电 | 未放行，未验证 |

**当前 U2 的 54 个非显示引脚均连接至同网过孔或另一目标焊盘；其中 47 个通过铜线连到同网过孔，7 个采用直接同层连接。原生检查已确认非显示网络全部连通，但不证明板子可启动。**
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

KiCad 10 若支持 `--refill-zones --save-board`，脚本自动采用该功能。整个原生检查在独立 `checked_project` 副本中进行，源 PCB 不被重写。原生路径已端到端执行；当前结果见 `verification/latest_attempt.json`，本次布线说明见 `docs/MINBOOT_ROUTING.md`。

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
