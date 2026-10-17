# 工具与复现

这些是生成／复查工程候选的本地脚本，没有对外写入账户或上传文件，也没有自动下单功能。生成源代码一并交付便于追溯，但任何“检查通过”须按检查本身的范围解释。

## 已用环境

使用 Python、Shapely 几何运算、C++ A* 辅助路径搜索、CadQuery 包络建模、ReportLab/PyMuPDF 绘图和自建 KiCad S 表达式写入／读取器。当前环境没有 kicad-cli 或 pcbnew。安装下载尝试失败记录在 `../reports/environment_apt_failure.log`；原生检查入口的运行结果记录在 `../reports/native_kicad8/native_attempt.json`。后者是未执行说明，不是 ERC／DRC 报告。

## 重建审查文件

需可用 Python 3、requirements.txt 中依赖、C++17 的 g++ 和系统 Cairo／OpenCascade 相关依赖。CAD 模型由 CadQuery 导出；可根据系统安装方法提供相应共享库。辅助路由 C++ 动态库在本地 `tools/.build/` 编译，不随包分发二进制。

```sh
python3 -m pip install -r tools/requirements.txt
sh tools/rebuild_review.sh
```

**会覆盖 CAD、CAM、图、检查报告等生成文件。先备份任何人工修改。** 构建顺序为模型→非 DSI 候选布线→静态几何→STEP 包络→原生格式文件→自定义 CAM→连接性和位号校验→审查图／表。脚本永远不推断缺失 W/S，所以 DSI 仍不布线。随机性被尽量移除，但库版本变化可能改变多边形片元、序列化字节或 PDF 元数据；不能承诺跨版本字节级完全相同。

`write_kicad.py` 会重写 `.kicad_pcb`，所以任何 CAM／检查之前必须重新运行 `export_review.py` 和 `validate_review.py`；禁止先导出后修改 PCB 却沿用旧 SHA-256。地铜填充为自定义几何缓存，不是 KiCad 重填结果。

## 真正的 KiCad 8 原生验证

在安装 KiCad 8.x 的机器上，使用能导入其 pcbnew 的 Python 运行：

```sh
python3 tools/validate_in_kicad8.py
```

它把 kicad 目录复制到 `reports/native_kicad8/candidate_kicad/`，尝试原生重新填铜，然后执行 KiCad 8 的原理图 ERC 与 PCB DRC，保留 JSON 和标准输出。缺少工具、版本不符、加载失败或检查失败都会保留状态，不写成“0 错误”。即使返回码为 0，也仍然不批准投产；必须检查日志和报告，并完成 DSI、线缆、电源／屏时序、采购及物理装配门槛。当前版本四条 DSI 未连通，预期不能通过完整 DRC 验收。

脚本不会自动修改数据去消除检查项，不会替你批准豁免，也不会把某个更新版 KiCad 的结果谎称为 KiCad 8 的结果。若原生读取报告格式不兼容，需按错误信息修正生成器／工程后再次执行，而非忽略失败。

## 检查范围

- `inspect_geometry.py`：元件名义本体、孔避让、线宽／铜距、过孔到任何焊盘边以及盘中孔。
- `validate_review.py`：四根 DSI 的条件网表极性、NC、孔位行距、分层导体几何连通、BOM/CPL/DNP 集合、CAM 文件与原 PCB 哈希、内层 ZIP CRC。
- `native_io.py`：仅显式 S 表达式读写，不是完整 KiCad 文件规范校验器。
- `make_previews.py`／`render_layout.py`：审查视图，不是原生截图。
- `make_envelopes.py`：已知尺寸的器件本体包络；不模拟触点、锁扣行程或未知高度。
- `make_manifest.py`：最终完整性哈希，不是电路合格证明。

静态连通检查允许微小浮点容差，不能取代原生 netlist／pad connectivity；自定义铺铜和描字也不构成制板厂认可的 CAM。发布时应使用核验后的原生工程再导出最终制造文件。