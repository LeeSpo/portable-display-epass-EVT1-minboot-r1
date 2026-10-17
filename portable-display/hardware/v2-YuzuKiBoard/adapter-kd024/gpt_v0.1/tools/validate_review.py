#!/usr/bin/env python3
"""Independent static evidence for this engineering review, NEVER native ERC/DRC."""
from geometry import *
from native_io import read_pcb,parse,children,child
from shapely import wkt
import json,csv,hashlib,shutil,subprocess,math,zipfile,sys
b=load();p=read_pcb();report={'fabrication_released':False,'validation_kind':'CUSTOM_STATIC_NOT_KICAD_ERC_DRC'}
report['pcb_sha256']=hashlib.sha256((ROOT/'kicad/adapter_v0.1.kicad_pcb').read_bytes()).hexdigest()
files=list((ROOT/'kicad').glob('*.kicad_sch'))+list((ROOT/'kicad').glob('*.kicad_sym'))+list((ROOT/'kicad/Adapter.pretty').glob('*.kicad_mod'))
for f in files:parse(f.read_text())
report['sexpression_balanced_files']=len(files)+1
report['sexpression_caveat']='Balanced syntax only; native parser/schema/application opening NOT VERIFIED'
report['native_erc']={'status':'NOT_RUN','errors':None,'waivers':[]}
report['native_drc']={'status':'NOT_RUN','errors':None,'waivers':[]}
report['kicad_cli_path']=shutil.which('kicad-cli')
report['counts']={'parts':len(b['parts']),'core_pads':len(b['pads']),'tracks':len(p['tracks']),'vias':len(p['vias']),'nets':len(b['nets'])}
# Pin contracts and expected directed mappings.
lookup={(a['ref'],a['num']):a for a in b['pads']}
for j1,j2,net in [('2','36','DSI_D0_N'),('3','35','DSI_D0_P'),('5','40','DSI_CK_N'),('6','39','DSI_CK_P')]:
 assert lookup['J1',j1]['net']==lookup['J2',j2]['net']==net
for pin in ['8','9','16','20','21','22','24']:assert not lookup['J1',pin]['net']
assert not any(t['net'] in b['dsi_nets'] for t in p['tracks'])
assert not any(v['net'] in b['dsi_nets'] for v in p['vias'])
report['dsi']={'status':'FOUR_NETS_UNROUTED','W_mm':None,'S_mm':None,'impedance_ohm':None,'actual_end_to_end_lengths_mm':None,'target_ohm':100,'length_match_pass':False}
# Source-Gerber rigid transform and 19.913 row separation.
rows=[]
for ref in ['H1','H2']:
 for a in [a for a in b['pads'] if a['ref']==ref]:
  rows.append([ref,a['num'],f'{a["x"]-35:.6f}',f'{82-a["y"]:.6f}',f'{a["x"]:.6f}',f'{a["y"]:.6f}',a['drill'],a['w'],a['net'] or 'NC'])
assert abs(lookup['H2','1']['y']-lookup['H1','1']['y']-19.913)<1e-6
report['header_row_spacing_mm']=19.913
# All routed copper islands checked on the custom fill, including vias between layers.
fills={k:wkt.loads(v) for k,v in json.loads((ROOT/'reports/zone_geometry.json').read_text()).items()}
connect=[]
for net in b['nets']:
 pads=[a for a in b['pads'] if a['net']==net];islands=[]
 for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']:
  gs=[pad_shape(a) for a in pads if a['kind']=='thru_hole' or layer=='F.Cu']
  gs += [track_shape(t) for t in p['tracks'] if t['net']==net and t['layer']==layer]
  gs += [via_shape(v) for v in p['vias'] if v['net']==net]
  if net=='GND':gs.append(fills[layer])
  if gs:
   for g in polys(unary_union([g.buffer(.000002) for g in gs])):islands.append((layer,g))
 parent=list(range(len(islands)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def join(indices):
  if indices:
   r=root(indices[0])
   for i in indices[1:]:parent[root(i)]=r
 for v in [v for v in p['vias'] if v['net']==net]+[{'x':a['x'],'y':a['y']} for a in pads if a['kind']=='thru_hole']:
  join([i for i,(ly,g) in enumerate(islands) if g.covers(Point(v['x'],v['y']))])
 pad_islands={}
 for a in pads:
  idx=[i for i,(ly,g) in enumerate(islands) if (ly=='F.Cu' or a['kind']=='thru_hole') and g.intersects(pad_shape(a))]
  assert idx, (net,a['ref'],a['num'])
  pad_islands[a['ref']+':'+a['num']]=root(idx[0])
 groups={}
 for k,v in pad_islands.items():groups.setdefault(v,[]).append(k)
 connect.append({'net':net,'pad_component_count':len(groups),'groups':list(groups.values()),'expected_unrouted':net in b['dsi_nets']})
report['connectivity']=connect
report['unexpected_disconnected_nets']=[c['net'] for c in connect if c['pad_component_count']!=1 and not c['expected_unrouted']]
# BOM/CPL/dnp attribute parity.
def rc(path):
 with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
bom=rc(ROOT/'manufacturing/adapter_v0.1_bom.csv');cpl=rc(ROOT/'manufacturing/adapter_v0.1_cpl.csv');dnp=rc(ROOT/'manufacturing/adapter_v0.1_bom_dnp.csv')
fit={a['ref'] for a in p['parts'] if not a['dnp'] and not a['feature']}
assert {a['Designator'] for a in bom}=={a['Designator'] for a in cpl}==fit
assert all(a['Layer']=='Top' for a in cpl)
assert {a['Designator'] for a in dnp}=={'H1','H2','R8'}
report['assembly']={'bom_cpl_parity':True,'top_fitted':len(fit),'dnp':['H1','H2','R8'],'jlc_previewer_status':'NOT_RUN','library_class_all_verified':False}
manifest=json.loads((ROOT/'manufacturing/CAM_MANIFEST.json').read_text())
assert manifest['pcb_sha256']==report['pcb_sha256']
assert len([x for x in manifest['files'] if x.get('layer') in ['F.Cu','In1.Cu','In2.Cu','B.Cu']])==4
assert len([x for x in manifest['files'] if x.get('layer')=='Edge.Cuts'])==1
for x in manifest['files']:
 txt=(ROOT/'manufacturing'/x['file']).read_text()
 assert report['pcb_sha256'] in txt
 if x['file'].endswith('.drl'):assert 'METRIC,TZ' in txt
 else:assert '%MOMM*%' in txt and txt.count('G36*')==txt.count('G37*')
with zipfile.ZipFile(ROOT/'manufacturing/adapter_v0.1_gerber.zip') as z:assert z.testzip() is None
report['cam']={'four_copper_layers':True,'outline_closed_paths':1,'units':'mm','origin_xy_pcb_mm':[50,82],'gerber_zip_crc':'PASS','exporter':'CUSTOM_NOT_KICAD'}
report['static_geometry']=json.loads((ROOT/'reports/static_geometry.json').read_text())
report['unresolved_gates']=['Native KiCad 8 open/zone refill/ERC/DRC','Official JLC04101H-3313 calculator W/S','Four DSI routes and length/clearance tuning','Physical FFC continuity and screen -4591/-4593 compatibility','Panel-approved default bias and MIPI power sequencing','Procurement MPN/LCSC/basic-library and assembly rotation','Power-loop/thermal/current review and sample tests']
(ROOT/'reports/validation_summary.json').write_text(json.dumps(report,indent=2))
def wc(name,head,rr):
 with open(ROOT/'reports'/name,'w',newline='',encoding='utf-8-sig') as f:w=csv.writer(f);w.writerow(head);w.writerows(rr)
wc('header_coordinates.csv',['Ref','Pin','Gerber_X_mm','Gerber_Y_mm','PCB_X_mm','PCB_Y_mm','Drill_mm','Pad_mm','Net'],rows)
wc('DSI_lengths.csv',['Net','J1_pin','J2_pin','Status','W_mm','S_mm','End_to_end_length_mm','PN_skew_limit_mm','Pair_to_pair_limit_mm'],[[net,next(a['num'] for a in b['pads'] if a['net']==net and a['ref']=='J1'),next(a['num'] for a in b['pads'] if a['net']==net and a['ref']=='J2'),'UNROUTED / NOT COMPLIANT','','','',.15,1.] for net in b['dsi_nets']])
wc('component_selection.csv',['Designator','Value','Footprint','MPN','LCSC','Library_class','DNP','Selection_reason'],[[a['ref'],a['value'],a['footprint'],a['mpn'],a['lcsc'],a['library_class'],a['dnp'],a['reason']] for a in b['parts'] if not a['feature']])
wc('pin1_rotation.csv',['Designator','Rotation_deg','PCB_origin_X','PCB_origin_Y','Pin1_X','Pin1_Y','Native_3D_verified'],[[a['ref'],a['angle'],a['x'],a['y'],lookup[a['ref'],'1']['x'],lookup[a['ref'],'1']['y'],'NO'] for a in b['parts'] if a['ref'] in ['J1','J2','U1','U2','U3','U4']])
print('Static connectivity: unexpected disconnected nets',report['unexpected_disconnected_nets'])
print('BOM / CPL parity PASS; native ERC / DRC NOT RUN; fabrication HOLD.')
print(report['pcb_sha256'])
