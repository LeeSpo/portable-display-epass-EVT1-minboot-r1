from audit import *
import subprocess
main=C/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb';v=C/'verification'
a=audit(main,v/'drc.json');sha=a['board_sha256'];date='2026-09-20'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def writejson(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
writejson(v/'drc_provenance.json',{'board_sha256':sha,'project_sha256':digest(main.with_suffix('.kicad_pro')),'drc_sha256':digest(v/'drc.json'),'kicad_version':'10.0.6','command':'kicad-cli pcb drc --refill-zones --save-board --format json','date':date,'drc_rules_unchanged':True,'fabrication_released':False})
subprocess.run([sys.executable,str(R/'verify_layout.py'),str(main),'--output',str(v/'geometry_audit.json')],check=True,stdout=subprocess.DEVNULL)
old=json.loads((W/'before_promotion/verification/assessment.json').read_text());r=RepairRouter(rb.load(main))
assessment=dict(a);assessment['length_measurement']='Sum of all track segments, not routed pin-to-pin skew or an impedance result';assessment['nand_absent']=old.get('nand_absent');assessment['placement_changes_from_main']=old['placement_changes_from_main']+[{'ref':'C38','before':a['placement_changes_this_repair']['C38'][0],'after':a['placement_changes_this_repair']['C38'][1]}]
assessment['zones']=[{'net':z.net,'layer':next(iter(z.layers)),'filled_area_mm2':round(z.geom.area,4),'label':z.label} for z in r.zones]
assessment['power_pad_groups']=a['ground_power_pad_groups'];writejson(v/'assessment.json',assessment)
oldvip=json.loads((W/'before_promotion/verification/via_in_pad_audit.json').read_text());oldkeys={(e['pad'],tuple(e['pos'])) for e in oldvip['locations']}
vips=[{'via':e['via_uuid'],'pos':e['at_mm'],'pad':e['pad'],'net':e['net']} for e in a['via_in_pad']];newvips=[e for e in vips if (e['pad'],tuple(e['pos'])) not in oldkeys];nv=len(set(e['via'] for e in vips))
writejson(v/'via_in_pad_audit.json',{'board_sha256':sha,'scope':'Drill intersects SMD copper; counts are via/pad intersections; no process approval inferred','intersections':len(vips),'unique_vias':nv,'locations':vips,'new_intersections_this_repair':newvips,'assembly_status':'Filled/capped process and stencil/reflow qualification required'})
writejson(v/'u1_u2_repair_audit.json',a)
p=C/'FOOTPRINT_REVIEW_CN.md';s=p.read_text().replace('核查日期：2026-09-10 至 2026-09-11。','核查日期：2026-09-10 至 2026-09-20。本次追加修复仅针对 split power 的 U1/U2 及相关布线。')
s=s.replace('F.Fab 改为 9×9 mm；原 5.2×5.2 mm EP 与外围铜焊盘暂保留，尚未取得厂家推荐 PCB land。','本体保持 9×9 mm；EP 改为 6.5×6.5 mm，外围 land 为 0.70×0.18 mm、径向中心 ±4.40 mm；EP 钢网 4×4 分窗。')
s=s.replace('F.Fab 改为 5×5 mm；原 3.1×3.1 mm EP 与外围铜焊盘暂保留，推荐 PCB land 尚未确认。','本体保持 5×5 mm；EP 改为 3.4×3.4 mm，外围 land 为 0.70×0.20 mm、径向中心 ±2.40 mm；EP 钢网 2×2 分窗。')
start=s.index('## U1、U2 仍需确认的内容');end=s.index('## 原始依据',start)
s=s[:start]+'''## U1、U2 铜焊盘修复（2026-09-20）

原本体轮廓和引脚节距正确，但外围铜焊盘偏外，标称端子与 PCB land 的径向重叠只有约 0.10 mm；EP 也偏小。本次按厂家机械图的标称尺寸设计工程 land，并重新完成扇出、供电与接地连接。

| 项目（mm） | U1 AXP2101 | U2 V851S |
|---|---|---|
| 本体 / 引脚节距 | 5×5 / 0.40 | 9×9 / 0.35 |
| 外围铜焊盘长×宽 | 0.70×0.20 | 0.70×0.18 |
| 外围铜焊盘径向中心 | ±2.40（原 ±2.75） | ±4.40（原 ±4.75） |
| EP 铜焊盘 | 3.40×3.40（原 3.10×3.10） | 6.50×6.50（原 5.20×5.20） |
| EP 钢网分窗 | 2×2，每窗 1.35×1.35、中心距 1.70 | 4×4，每窗 1.30×1.30、中心距 1.60 |
| 计入圆角的开口面积占比 | 62.93% | 63.86% |

外围 land 标称端子重叠约 0.40 mm，heel/toe 余量约 0.05/0.25 mm；铜焊盘阻焊扩展 0.025 mm。EP 使用铜层和阻焊层，钢网由独立的无编号 F.Paste 窗口定义，避免整个 EP 全开。窗口圆角比例为 0.05。编号焊盘与网络不变，板上封装和本地 QFN40/QFN88 库一致。

这是依据机械尺寸和 QFN 装联指南制定的工程 land，**不是厂家发布的推荐 PCB land 图**。最终钢网厚度、锡膏转移率、空洞率及填孔封帽工艺仍须装联审核。所用约 63% 开口率位于 TI SLUA271C §4.4 的 50%～70% 建议范围；该通用指南不替代这两个芯片的装联资格确认。

相关布局只将 C38 从 (25.50,55.35) 移至 (25.50,55.75)，旋转角保持 -90°，为 U1 的信号过孔和 VBUS 引线留出通道。其余元件中心及旋转不变。关键 MIPI、USB、SD_CLK、晶振和 LX/SW 路径仍在 F.Cu，无过孔。原生 DRC、二维几何、逐引脚网络和接地连续性检查通过；高速性能与电源载流尚未签核。

'''+s[end:]
s=s.replace('以上结论不能替代', '- [TI QFN/SON PCB Attachment 指南](https://www.ti.com/lit/pdf/slua271)，SLUA271C，2023-12，§3.3、3.4、4.4；用于工程 land 与分窗方法。\n\n以上结论不能替代');p.write_text(s)
(C/'README_CN.md').write_text(f'''# 四层分区供电候选

{date}：**U1/U2 铜焊盘、EP 与钢网分窗已修复并同步本地库；最终主文件原生 DRC 为 0 未连接、0 违规、0 告警。当前为工程候选，尚未投板放行。**

打开本目录 `ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pro` 或 `.kicad_pcb`，并保留 `sameat.pretty` 与 `fp-lib-table`。

## 本次修复

- U1 AXP2101：本体 5×5 mm、节距 0.40 mm；外围铜焊盘 0.70×0.20 mm、径向中心 ±2.40 mm；EP 3.40×3.40 mm，钢网 2×2 分窗。
- U2 V851S：本体 9×9 mm、节距 0.35 mm；外围铜焊盘 0.70×0.18 mm、径向中心 ±4.40 mm；EP 6.50×6.50 mm，钢网 4×4 分窗。
- 按新焊盘重新扇出，补齐供电/控制信号和接地连接，清理残线与多余过孔。C38 向下微移 0.40 mm，其余元件中心和旋转不变。
- 119 个封装均在正面，逐引脚网络映射一致，NAND 保持删除，板框仍为 38×64 mm。此前 U4/U5/U6/U8/U9 的封装修正保持，详见 [封装核查记录](FOOTPRINT_REVIEW_CN.md)。
- MIPI、USB、SD_CLK、晶振、LX/SW 仍全部在 F.Cu，无换层过孔；层别检查通过不代表高速性能合格。

## 层与验证

| 层 | 用途 |
|---|---|
| F.Cu | 元件、关键线路、局部供电及接地铜 |
| In1.Cu | GND，一个连续填充多边形，无信号走线 |
| In2.Cu | 分区供电、GND 及局部信号跨接 |
| B.Cu | 辅助信号、局部供电及接地铜 |

In2 的走线总长由 14.2399 mm 增至 {a['in2_track_length_mm']:.4f} mm，含供电和信号；具体网络长度见 `verification/assessment.json`。这会改变电源铜区形状，实际载流及回流路径仍需结合电流和层叠审核。

KiCad 10.0.6 按原工程规则检查，未改变规则、降低严重级别或新增豁免。GND 和六个复查电源网络的焊盘各为一个连通组。二维几何检查通过：最小 courtyard 间距 0.302076 mm，不同网络焊盘最小间距 0.15 mm，未进入预留区。

## 文件与追溯

- [四层预览](four_layers.png)，四个原生 SVG 位于 `verification/layers/`。
- `verification/drc.json`、`drc_provenance.json`：与最终主文件哈希对应的 DRC。
- `verification/geometry_audit.json`、`assessment.json`：几何、引脚网络、层别、铜线长度及摆件变化。
- `verification/u1_u2_repair_audit.json`：本次封装、钢网、网络与接地核查。
- `verification/via_in_pad_audit.json`：{len(vips)} 处钻孔/SMD 焊盘相交记录，涉及 {nv} 个不同过孔，仍须确认填孔封帽和装联工艺。
- `verification/u1u2_repair_20260919/before_promotion/`：本轮覆盖前的 PCB、两个 QFN 库和旧报告备份；同级过程检查点仅供追溯。

本轮 land 是根据厂家机械图制定的工程设计，仍需装联资格确认；高速差分线、实际层叠/载流、J4 机械接口及原理图/ERC 的未完成项见 [验收记录](OPEN_ISSUES_CN.md)。没有生成生产 Gerber 或提交生产订单。
''')
k=a['critical_nets'];p=C/'OPEN_ISSUES_CN.md';s=p.read_text().replace('更新：2026-09-11。','更新：2026-09-20。').replace(a['original_board_sha256'],sha)
lines=s.splitlines()
for i,line in enumerate(lines):
 if line.startswith('1. **U1/U2'):
  lines[i]='1. **U1/U2 装联资格确认。** 铜焊盘、EP 和钢网分窗已按厂家机械尺寸及通用 QFN 指南完成工程修复，并通过 DRC；并非厂家推荐 land 的认证。最终钢网厚度、锡膏转移、空洞率、填孔封帽与试焊仍待确认。详见 [封装核查](FOOTPRINT_REVIEW_CN.md)。'
 elif line.startswith('2. **MIPI'):
  lines[i]=f"2. **MIPI 差分匹配与耦合优化。** CK N/P 总铜线长为 {k['DSI_CKN']['total_copper_length_mm']}/{k['DSI_CKP']['total_copper_length_mm']} mm，D0 N/P 为 {k['DSI_D0N']['total_copper_length_mm']}/{k['DSI_D0P']['total_copper_length_mm']} mm。仍不能作为合格高速差分线交付，需结合 J4 最终引脚位置和实际层叠重布、约束并验证。"
 elif line.startswith('3. **USB'):
  lines[i]=f"3. **USB 差分路径与阻抗。** DM/DP 总铜线长为 {k['USB_DM']['total_copper_length_mm']}/{k['USB_DP']['total_copper_length_mm']} mm，均在顶层且无过孔。总铜长包含分支，不等于端到端偏斜，仍需检查耦合、支路和实际阻抗。"
 elif line.startswith('4. **焊盘'):
  lines[i]=f'4. **焊盘内过孔工艺。** 有 {len(vips)} 处钻孔与 SMD 铜焊盘相交，涉及 {nv} 个不同过孔。新增交叠包括 U1.6/U1.7、C14.2、C37.2、C51.2、R22.1、C32.1、D10.1 和 J5.7，详见 `verification/via_in_pad_audit.json`。须确认填孔封帽与装联工艺，或移出焊盘并重新布线；不能按普通开放通孔默认生产。'
 elif line.startswith('5. **供电'):
  lines[i]=f"5. **供电压降、载流及回流。** 复查电源和 GND 已连通；保留 0.60/0.30 mm 过孔和局部细颈，连通不证明载流。In2 走线由 14.2399 增至 {a['in2_track_length_mm']} mm，局部跨接改变电源区形状。须结合峰值电流、铜厚、介质层及温升评估压降和回流。"
s='\n'.join(lines)+'\n';s=s.replace('## 已关闭的问题\n','## 已关闭的问题\n\n- U1/U2 原外围 land 偏外、EP 偏小及整面钢网开口已修复，关联布线/接地与封装库同步完成；本次仅移动 C38 向下 0.40 mm。\n');p.write_text(s)
(C/'GUI_FOLLOWUP_CN.md').write_text('''# KiCad 检查方式记录

2026-09-20 的 U1/U2 修复以保存后的主 PCB、KiCad 10.0.6 原生 CLI DRC、独立二维几何与连通审计为验收依据。最终结果为 0 未连接、0 违规、0 告警；报告见 `verification/drc.json` 及对应文件哈希。

曾尝试编辑器 Interactive Router 的 Shove 模式，但界面控制点击位置与实际选中对象不一致，因此没有采用或保存该尝试的交互布线修改。随后通过精确坐标调整局部线路，并由原生 DRC 验证。不能将此记录表述为已完成交互推挤布线或 GUI 手工签核。

四层预览与原生 SVG 已从最终主文件重新生成。2026-09-11 的旧窗口检查记录存放于本轮 `verification/u1u2_repair_20260919/before_promotion/`，不代表最新板文件。

当前状态以 `README_CN.md`、`FOOTPRINT_REVIEW_CN.md`、`OPEN_ISSUES_CN.md` 与哈希匹配的验证报告为准；仍未完成生产验收。
''')
p=W/'README.md';s=p.read_text();s=s.replace('`work.kicad_pcb` is a WORK IN PROGRESS until the final report explicitly records native KiCad DRC = 0 violations / 0 unconnected. Do not fabricate from intermediate checkpoints. Original candidate saved as `original.kicad_pcb`. Main candidate is not replaced until verification passes.','Completed 2026-09-20: validated repair promoted to the main split-power candidate and QFN libraries. Native KiCad DRC: 0 violations, 0 unconnected. Matching final audit: `final_audit.json`. Intermediate numbered checkpoints are historical WIP and must not be used for fabrication. Original candidate is `original.kicad_pcb`; complete pre-promotion backups are in `before_promotion/`. The final candidate still requires assembly and system qualification.')
s=s.replace('All placements, numbered pad net assignments, board shape and project rules retained.','C38 moved from (25.50,55.35) to (25.50,55.75), angle -90° unchanged; all other placements retained. Numbered pad net assignments, board shape and project rules retained.');p.write_text(s)
p=R/'SHA256SUMS.txt';s=p.read_text().splitlines();s=[digest(R/'verify_layout.py')+'  verify_layout.py' if line.endswith('  verify_layout.py') else line for line in s];p.write_text('\n'.join(s)+'\n')
print('Published report hash',sha,'VIP intersections',len(vips),'unique vias',nv)
