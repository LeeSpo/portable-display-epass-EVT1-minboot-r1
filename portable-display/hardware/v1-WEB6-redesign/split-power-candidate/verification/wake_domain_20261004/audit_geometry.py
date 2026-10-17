from pathlib import Path
import sys,json,hashlib,collections,math
BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE.parent/'tools'))
from plane_connectivity import zones,connected_groups
from geometry_audit import board_items
import kicad_sexpr as s
P=BASE;OUT=P/'verification/wake_domain_20261004';file=P/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb';b=s.load(file);old=s.load(OUT/'before.kicad_pcb');its=board_items(b);prior=board_items(old)
fs={s.props(f)['Reference']:f for f in s.children(b,'footprint')};oldfs={s.props(f)['Reference']:f for f in s.children(old,'footprint')}
assert all(s.values(fs[r],'at')==s.values(f,'at') for r,f in oldfs.items()),'Existing part moved'
def objects(tree,net):return {s.dumps(n) for n in tree if isinstance(n,list) and n[0] in ['segment','via'] and s.val(n,'net')==net}
critical=['USB_DP','USB_DM','DSI_CKP','DSI_CKN','DSI_D0P','DSI_D0N','WAKE_PULSE','WAKE_PULSE_N','WAKE_REXT','WAKE_CEXT','WAKE_REQ_N','PWRON_N','I2C0_SDA','I2C0_SCL']
unchanged={n:objects(b,n)==objects(old,n) for n in critical};assert all(unchanged.values()),unchanged
physical=its+zones(b);nets=sorted({i.net for i in its if i.kind=='pad' and i.net and not i.net.startswith('unconnected-')});groups={}
for n in nets:
 gs=[g for g in connected_groups([i for i in physical if i.net==n]) if any(i.kind=='pad' for i in g)];groups[n]=len(gs)
assert all(v==1 for v in groups.values()),{n:g for n,g in groups.items() if g!=1}
oldvia={i.label for i in prior if i.kind=='via'};hits=[]
for v in its:
 if v.kind!='via':continue
 for p in its:
  if p.kind=='pad' and p.hole is None and v.hole.distance(p.geom)<1e-9:hits.append({'via':v.label,'pos':v.pos,'pad':p.label,'new_via':v.label not in oldvia})
assert not any(h['new_via'] for h in hits),hits
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'board_sha256':sha(file),'new_components':['U11','C52'],'all_existing_placements_unchanged':True,'critical_copper_unchanged':unchanged,'connected_pad_groups':groups,'all_electrical_nets_connected':True,'physical_net_count':len(nets),'footprint_count':len(fs),'numbered_pad_count':sum(1 for i in its if i.kind=='pad' and i.pin),'new_vias':len([i for i in its if i.kind=='via' and i.label not in oldvia]),'new_vias_intersecting_smd_pads':0,'via_in_pad_pairs_total':len(hits),'via_in_pad_vias_total':len({h['via'] for h in hits}),'in2_total_track_mm':sum(math.dist(*i.pos) for i in its if i.kind=='track' and 'In2.Cu' in i.layers),'project_rules_unchanged':sha(P/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pro')==sha(OUT/'before.kicad_pro'),'copper_items_by_net':dict(collections.Counter(i.net for i in its if i.kind!='pad'))}
assert report['project_rules_unchanged']
(OUT/'change_audit.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'via_in_pad_audit.json').write_text(json.dumps({'intersections':hits,'new_intersections':0},indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['copper_items_by_net','connected_pad_groups']},indent=2))
