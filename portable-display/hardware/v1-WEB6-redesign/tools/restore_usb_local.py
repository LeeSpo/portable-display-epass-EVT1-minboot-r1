import sys,copy,json,uuid
from pathlib import Path
from shapely.geometry import box,LineString
sys.path.insert(0,'portable-display/hardware/v1-WEB6-redesign/tools')
from route_verified import VerifiedRouter,rb
from plane_connectivity import children,values,val,dumps
p=Path('portable-display/hardware/v1-WEB6-redesign/split-power-candidate/verification/routing_20260910/work.kicad_pcb');b=rb.load(p);p.with_name('before_usb_local_restore.kicad_pcb').write_text(dumps(b))
area=box(0,51,38,64);out=[];rem=[];keep=[]
for n in b:
 if isinstance(n,list) and n and n[0]=='segment' and str(val(n,'net')) in ['USB_DP','USB_DM']:
  pts=[tuple(map(float,values(n,k))) for k in ['start','end']];ln=LineString(pts)
  if ln.intersects(area):
   rem.append(str(val(n,'uuid')));diff=ln.difference(area)
   if not diff.is_empty:
    for ls in ([diff] if diff.geom_type=='LineString' else list(diff.geoms)):
     nn=copy.deepcopy(n);children(nn,'start')[0][1:]=[str(v) for v in ls.coords[0]];children(nn,'end')[0][1:]=[str(v) for v in ls.coords[-1]];children(nn,'uuid')[0][1]=rb.q(str(uuid.uuid4()));out.append(nn);keep.extend([ls.coords[0],ls.coords[-1]])
   continue
 out.append(n)
b=out
# Free the direct flow-through paths and connector fanout by moving auxiliary traces to the back.
paths={'USB_DP':[[(17.7,51),(17.775,51.075),(17.775,53.55),(17.775,55.85),(19.75,55.85),(19.75,57.72)],[(19.75,57.72),(19.75,58.6),(18.75,58.6),(18.75,57.72)]],
'USB_DM':[[(14.6,51),(14.6,51.4),(15.875,52.675),(15.875,53.55),(15.875,55.85),(15.875,56.6),(19.25,56.6),(19.25,57.72)],[(18.25,56.6),(18.25,57.72)]]}
items=rb.board_items(b);rm=set();blocked=[]
for net,ps in paths.items():
 for pts in ps:
  geom=LineString(pts).buffer(.09+.127)
  for i in items:
   if i.net!=net and 'F.Cu' in i.layers and geom.intersects(i.geom):
    if i.kind in ['track','via'] and i.net not in ['USB_DP','USB_DM']:rm.add(i.label)
    else:blocked.append((net,i.label,i.net))
b=[n for n in b if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'uuid')) in rm)]
p.write_text(dumps(b)+'\n');rb.BOARD=p;r=VerifiedRouter(b);result={'preserved_trunk_endpoints':keep,'removed_usb_segments':len(rem),'reroute_aux_nets':sorted({i.net for i in items if i.label in rm}),'pad_blockers':blocked,'routes':[]}
for net,ps in paths.items():
 for pts in ps:
  ok=r.commit_xy([(*q,'F.Cu') for q in pts],.18,net);result['routes'].append({'net':net,'ok':ok,'pts':pts})
r.write();(p.parent/'usb_direct_restore.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
