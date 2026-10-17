# 蜥蜴 → KD024 单通道 DSI 转接板

## v0.1 工程审查包：禁止直接生产／接屏上电

已按任务书完成可生成部分，保留了无法核实的制造与电气门槛。**本包不是满足全部验收条件的生产版**：四根 DSI 未布线，指定阻抗计算未完成，原生 KiCad 8 ERC／DRC 未运行，FFC 方向与屏偏压／时序尚待确认。不要把内层 `adapter_v0.1_gerber.zip` 上传生产。

先阅读 `DESIGN_NOTES.md`，再查看 `DFM_CHECKLIST.md` 与 `reports/validation_summary.json`。

| 目录／文件 | 内容 |
|---|---|
| `kicad/adapter_v0.1.kicad_pro` | 目标 KiCad 8 工程入口；原生打开未验证 |
| `kicad/*.kicad_sch`、`Adapter.kicad_sym` | 三张原理图及自建符号；每脚连网或 NC |
| `kicad/adapter_v0.1.kicad_pcb` | 42×38mm、四层、1.0mm 候选板，非 DSI 网络已布，DSI 保留断网 |
| `kicad/Adapter.pretty/`、`models/` | 自建封装和部分尺寸包络 STEP，非厂商完整 3D 模型 |
| `manufacturing/` | 同一 PCB 来源的审查用 CAM、钻孔、BOM、DNP、CPL 及 Gerber ZIP |
| `docs/adapter_v0.1_schematic.pdf` | 矢量原理图审查图，不是 KiCad 原生导出 |
| `previews/` | 顶层／叠层、1 脚角度、DSI 缺口、包络示意和原理图页图 |
| `docs/CABLE_AND_PIN_MAP.md` | 同面／反面条件线序表、危险反序说明和 J2 全引脚映射 |
| `docs/COMPONENT_SELECTION.md` | 每个位号选择理由、未确认物料和库分类 |
| `reports/` | 静态检查、逐脚孔位、DSI 长度缺口、旋转坐标、源 PCB 哈希及环境记录 |
| `tools/` | 可复现脚本、依赖和后续原生 KiCad 检查入口；运行前先备份手改文件 |
| `reference/brief_original/` | 用户原始任务及所有上传参考资料，原样保留 |
| `FILE_MANIFEST.sha256` | 外层包内文件完整性清单；不代表工程合格认证 |

### 当前硬件关键点

TPS65631 不直接接 5V：H1-13 经可调 LDO 产生标称 3.584V，再经 0603 0Ω 测流位供偏压。LCD_EN 外部 10kΩ 下拉，默认关闭。J1 3V3 仅供 1V8 与逻辑；VCI 单独取 H2-3。复位用 3.3V 容忍输入／1.8V 输出缓冲。D1 和背光高压脚保持 NC。

### 必须关闭的放行门槛

取得指定嘉立创叠层计算结果并布完 DSI，验证实际等长／间距；在 KiCad 8 重新填铜并完成 ERC／DRC 和封装／旋转检查；拿到线缆实物逐脚核对、屏厂批准的偏压及 MIPI 时序；确定采购 MPN、LCSC 和贴片工艺，再完成电源热／峰值与样板测试。当前不存在任何自动放行脚本，也没有声称已经点亮屏。