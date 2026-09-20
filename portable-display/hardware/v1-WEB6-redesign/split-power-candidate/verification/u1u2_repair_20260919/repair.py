import sys, json, shutil, uuid, math
from pathlib import Path
W=Path(__file__).resolve().parent; C=W.parents[1]; R=C.parent
sys.path.insert(0,str(R/'tools'))
from plane_connectivity import rb,children,values,val,dumps,zones,connected_groups
from kicad_sexpr import Q,setval
from geometry_audit import issues
from route_verified import VerifiedRouter
from route_remaining import route
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
P=W/'work.kicad_pcb'; rb.BOARD=P
CRITICAL={'DSI_D0N','DSI_D0P','DSI_CKN','DSI_CKP','USB_DP','USB_DM','XIN','XOUT','SD_CLK','LX_CORE','LX_DRAM','LX_3V3'}
def save(b):P.write_text(dumps(b)+'\n')
def cut(b,labels):return [n for n in b if not(isinstance(n,list) and n and n[0] in ('segment','via') and str(val(n,'uuid')) in labels)]
def setup():
 if P.exists():raise RuntimeError('work exists; refuse overwrite')
 src=C/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb'
 shutil.copy2(src,W/'original.kicad_pcb');shutil.copy2(src,P)
 shutil.copy2(src.with_suffix('.kicad_pro'),P.with_suffix('.kicad_pro'))
 shutil.copytree(C/'sameat.pretty',W/'sameat.pretty');shutil.copy2(C/'fp-lib-table',W/'fp-lib-table')
 b=rb.load(P)
 fps={str(next(x[2] for x in children(f,'property') if x[1]=='Reference')):f for f in children(b,'footprint')}
 for ref,name,old,new,ep,wide,count,pitch,ap in [('U1','QFN40',2.75,2.4,3.4,.2,2,1.7,1.35),('U2','QFN88',4.75,4.4,6.5,.18,4,1.6,1.3)]:
  lib=rb.load(W/'sameat.pretty'/f'{name}.kicad_mod')
  for f in [fps[ref],lib]:
   setval(f,'descr',Q(f'{ref}: manufacturer body/terminal dimensions; engineering land pattern 0.70 mm radial pads, segmented EP paste 63 percent; assembly qualification required'))
   for p in children(f,'pad'):
    x,y,*angle=map(float,values(p,'at'));sz=list(map(float,values(p,'size')))
    if abs(x)<.001 and abs(y)<.001:
     setval(p,'size',str(ep),str(ep));setval(p,'layers',Q('F.Cu'),Q('F.Mask'));setval(p,'zone_connect','2')
    else:
     if abs(abs(x)-old)<.001:x=math.copysign(new,x)
     if abs(abs(y)-old)<.001:y=math.copysign(new,y)
     setval(p,'at',str(x),str(y),*(str(a) for a in angle))
     setval(p,'size',*(str(v) for v in ([.7,wide] if sz[0]>sz[1] else [wide,.7])))
    setval(p,'solder_mask_margin','.025');setval(p,'solder_paste_margin','0');setval(p,'solder_paste_margin_ratio','0')
   for j in range(count):
    for k in range(count):
     f.append(['pad',Q(''),'smd','roundrect',['at',str((j-(count-1)/2)*pitch),str((k-(count-1)/2)*pitch)],['size',str(ap),str(ap)],['layers',Q('F.Paste')],['roundrect_rratio','.05'],['uuid',Q(str(uuid.uuid4()))]])
  (W/'sameat.pretty'/f'{name}.kicad_mod').write_text(dumps(lib)+'\n')
 save(b); b=rb.load(P); its=rb.board_items(b);byid={i.label:i for i in its};rem=set()
 for v in issues(its,clearance=.127):
  if not any(v[k].startswith(('U1.','U2.')) for k in ['a','b']):continue
  for k in ['a','b']:
   i=byid.get(v[k])
   if i and i.kind in ('track','via'):rem.add(i.label)
 save(cut(b,rem));print('Removed conflicts',len(rem),sorted(set(i.net for i in its if i.label in rem)),flush=True)
 prune();shutil.copy2(P,W/'01_footprints.kicad_pcb')
class RepairRouter(VerifiedRouter):
 routing_layers=['F.Cu','B.Cu','In2.Cu']
 def __init__(self,b):
  super().__init__(b);self.items=[i for i in self.items if i.layers or i.hole is not None];self._rebuild_tree();self.zones=zones(b)
 def groups(self,net):return [g for g in connected_groups([i for i in self.items+self.zones if i.net==net]) if any(i.kind=='pad' for i in g)]
 def endpoints(self,g):
  pts=[]
  for i in g:
   if i.kind in ('pad','via'):
    pts.extend([(*i.pos,l) for l in i.layers if l in self.routing_layers])
   elif i.kind=='track':pts.extend([(*p,next(iter(i.layers))) for p in i.pos])
  return list(set(p for p in pts if not getattr(self,'top_only',False) or p[2]=='F.Cu'))
 def _obstacles(self,net,width,layer):
  obs=super()._obstacles(net,width,layer)
  if layer=='In2.Cu' and abs(width-.6)>.00001:obs=unary_union([obs]+[i.geom.buffer(width/2+.127) for i in self.zones if i.net not in (net,'GND') and layer in i.layers])
  return obs.buffer(.0005)
 def _ok(self,geom,layers,net,hole=None):
  if hole is None and 'In2.Cu' in layers and any(i.net not in (net,'GND') and 'In2.Cu' in i.layers and i.geom.distance(geom)<.127-1e-6 for i in self.zones):return False
  return super()._ok(geom,layers,net,hole)
 def add_via(self,x,y,net):
  self.via_xy=[i.pos for i in self.items if i.kind=='via' and i.net!=net]
  try:return super().add_via(x,y,net)
  finally:self.via_xy=[i.pos for i in self.items if i.kind=='via']
def prune(nets=None):
 b=rb.load(P);its=rb.board_items(b)+zones(b);rem=set()
 for net in (nets or sorted(set(i.net for i in its if not rb.skip_net(i.net)))):
  ns=[i for i in its if i.net==net]
  for g in connected_groups(ns):
   if not any(i.kind=='pad' for i in g):rem.update(i.label for i in g if i.kind in ('track','via'))
  for _ in range(150):
   live=[i for i in ns if i.label not in rem];tree=STRtree([i.geom for i in live]);new=set()
   for i in live:
    if i.kind!='track':continue
    for p in i.pos:
     pt=Point(p)
     if not any(live[int(j)] is not i and live[int(j)].layers&i.layers and live[int(j)].geom.distance(pt)<1e-6 for j in tree.query(pt.buffer(1e-6))):new.add(i.label);break
   if not new:break
   rem.update(new)
 save(cut(b,rem));print('Pruned',len(rem),flush=True)
def status():
 r=RepairRouter(rb.load(P));out={n:[[i.label for i in g if i.kind=='pad'] for g in r.groups(n)] for n in sorted(set(i.net for i in r.items)) if not rb.skip_net(n) and len(r.groups(n))>1};print(json.dumps(out,indent=2));return out

def run(nets,step=.05,width=None):
 report=[]
 for net in nets:
  r=RepairRouter(rb.load(P));top=net in CRITICAL;r.top_only=top
  if top:r.routing_layers=['F.Cu','B.Cu']
  passes=[]
  for _ in range(20):
   rec=route(r,net,width or (.18 if net in rb.POWER else .127),step,top);passes.append(rec)
   if not rec['ok'] or len(r.groups(net))<2:break
  if r.added:r.write()
  result={'net':net,'groups':len(r.groups(net)),'passes':passes};report.append(result)
  (W/'latest_routes.json').write_text(json.dumps(report,indent=2)+'\n');print(net,'groups',result['groups'],passes[-1].get('reason'),flush=True)
  if result['groups']<2:prune([net])
 return report
if __name__=='__main__':
 cmd=sys.argv[1]
 if cmd=='setup':setup()
 elif cmd=='status':status()
 elif cmd=='prune':prune(sys.argv[2:] or None)
 elif cmd=='route':run(sys.argv[2:])
