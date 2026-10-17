# 资料来源与定位

检索日期：2026-10-16。只用制造商资料、官方工具文档和用户提供原始文件作为技术依据。链接是来源索引，不代表外部 PDF 已下载入本包；本地有副本的资料明确列出。

| 编号 | 来源 | 定位与用途 |
|---|---|---|
| S1 | `reference/brief_original/03_datasheets/molex_SD-502598-003.pdf` | SD-502598-003 Rev A，第 1–2 页：PCB 推荐图、奇偶脚错列、触点／锁扣、尺寸；第 3–4 页为编带 |
| S2 | `reference/brief_original/02_kd024_screen/KD024EGOIN152-01_SPEC_V1.pdf` | PDF 第 5 页管脚定义；第 13–14 页电气／电流表；第 16–17 页时序（图注为 SPI，不能直接假定适用于 MIPI）；第 22–24 页机械／FPC 信息。PDF 页号为文件中 1 起算，不是页面印刷页码 |
| S3 | `reference/brief_original/03_datasheets/tps65631.pdf`；https://www.ti.com/lit/ds/symlink/tps65631.pdf | Pin Configuration／Recommended Operating Conditions／Electrical Characteristics／Application Information；本地第 17 页布局图、第 22–24 页封装附录。输入 2.9–4.5V、CTRL、电感拓扑、缺省偏压及限流条件 |
| S4 | https://www.hirose.com/en/product/p/CL0580-1255-6-50 | FH34SRJ-24S-0.5SH(50) 官方产品页及 2D Drawing：EDC-159714-50-08；PDF 第 1 页推荐板图、第 4 页 24 位尺寸表、第 5 页起操作图。网页可见双接点信息，但实际线缆方向仍需核对 |
| S5 | https://www.coilcraft.com/en-us/products/power/shielded-inductors/molded-inductor/xfl/xfl4020/ ；https://www.coilcraft.com/getmedia/50632d43-da1b-4cdb-8ab4-3029cab51df3/xfl4020.pdf | XFL4020 官方参数，Document 1149，第 1 页电流／DCR 表、第 3 页外形与推荐焊盘；472MEC 行 |
| S6 | https://www.ti.com/lit/ds/symlink/tlv767.pdf | TLV767 手册：DRV6 管脚图、0.8V 基准与可调输出。附录图号 DRV0006A / 4222173/C 11/2025：Example Board Layout、Example Stencil Design。在线附录页数会随版本改变，应以图号检索，不以固定页号猜测 |
| S7 | https://www.ti.com/lit/ds/symlink/tlv755p.pdf | TLV755P／TLV75518PDBVR：DBV5 引脚图、固定 1.8V、输入／输出电容及封装图 |
| S8 | https://www.ti.com/lit/ds/symlink/sn74lvc1g17.pdf | SN74LVC1G17：1.65–5.5V 供电、输入容限、Ioff、VOH 条件、DBV5 引脚图 |
| S9 | https://jlcpcb.com/pcb-impedance-calculator ；https://jlcpcb.com/impedance | 官方计算器和叠层入口。未取得 JLC04101H-3313 本设计的有效参数／输出，不能用页面存在这一事实声称阻抗计算完成 |
| S10 | https://www.lcsc.com/zh-TW/product-detail/C5365339.html | 指定 C5365339 与 Molex 5025984593 的料号对应；不把料号对应等同于实时库存、基础库或 -4591/-4593 兼容认证 |
| S11 | `reference/brief_original/01_lizard_base/Yuzukilizard_gerber.zip`、`Yuzukilizard_altium.zip`、`Yuzukilizard_schematic.pdf` | 原始孔位、元件面别／方向与网络。H1/H2 实际 XY 来自钻孔／原板焊盘，不从 2.54mm 网格估计 |
| S12 | https://dev-docs.kicad.org/en/file-formats/sexpr-pcb/ ；https://docs.kicad.org/8.0/en/cli/cli.html | 目标文件结构与 KiCad 8 CLI 检查命令。只参阅文档不构成原生 KiCad 执行证明 |

## 用作参考而未盲从的文件

`reference/brief_original/04_reference_design/` 和屏的整理版 MD／JSON／CSV 用于交叉核对，冲突时以制造商／屏规格的原始图表为准。原版 TPS65631 电路说明并不是本板可以直接接 5V 的依据。屏规格中宽范围电压与典型测试点不同，也不能以范围含有默认偏压为理由免去屏厂批准。

## 证据缺口

未保存有效的嘉立创阻抗计算结果；未取得 KiCad 原生 ERC／DRC、KiCad 3D 或嘉立创贴片旋转截图；未获实际线缆与屏座相容性、排母高度、各轨峰值电流或屏厂 MIPI 初始化资料。生成的审查图和表不填补这些缺口。