from last_signals import *
import numpy as np, shapely
shutil.copy2(P,W/'30_before_ground.kicad_pcb')
r=RepairRouter(rb.load(P));gs=r.groups('GND');gs.sort(key=len,reverse=True);report=[]
for group in gs[1:]:
 pads=[i for i in group if i.kind=='pad'];geom=unary_union([i.geom for i in group]);x0,y0,x1,y1=geom.bounds
 xx,yy=np.meshgrid(np.arange(np.ceil(x0/.05),np.floor(x1/.05)+1)*.05,np.arange(np.ceil(y0/.05),np.floor(y1/.05)+1)*.05)
 mask=shapely.intersects_xy(geom.buffer(-.02),xx,yy);cands=list(zip(xx[mask],yy[mask]));cands.sort(key=lambda q:min(math.dist(q,p.pos) for p in pads));ok=False
 for x,y in cands:
  hole=Point(float(x),float(y)).buffer(.15)
  if any(hole.distance(i.geom)<.1 for i in r.items if i.kind=='pad' and i.layers):continue
  if r.add_via(float(x),float(y),'GND'):
   rec={'pads':[p.label for p in pads],'ok':True,'via':[float(x),float(y)]};ok=True;break
 if not ok:rec={'pads':[p.label for p in pads],'ok':False}
 report.append(rec);print(rec,flush=True)
if r.added:r.write()
(W/'ground_stitch.json').write_text(json.dumps(report,indent=2)+'\n')
run(['GND'],.025)
