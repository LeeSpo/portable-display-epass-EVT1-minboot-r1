# Portable Display

**不可直接投板、采购贴片或上电。**

## 目录

| 路径 | 内容 |
|---|---|
| [`docs/`](docs/) | 后续版本文档 |
| [`reference/`](reference/) | 后续版本参考资料 |
| [`hardware/v0_legacy/`](hardware/v0_legacy/) | 现有 EVT1-minboot 整包（原理图、PCB、工具、验证快照） |

## 打开工程

用 KiCad 9 或 10 打开：

`hardware/v0_legacy/portable_display_epass.kicad_pro`

符号和封装只引用工程目录里的本地库（`${KIPRJMOD}`）。

## 运行检查

在 `hardware/v0_legacy/` 下：

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/verify_evt1.py --static
```

原生 ERC/DRC：

```sh
python3 tools/verify_evt1.py
```

旧文档在 `hardware/v0_legacy/docs/`，旧参考资料在 `hardware/v0_legacy/reference/`。

`hardware/v0_legacy/ak_display_layout_38x64/` 是 38×64 mm 仅布局候选：未布线，不可投板。
