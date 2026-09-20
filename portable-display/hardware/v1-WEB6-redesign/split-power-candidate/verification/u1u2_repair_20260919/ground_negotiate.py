from last_signals import *
from fanout import force
import numpy as np
r=RepairRouter(rb.load(P));gs=sorted(r.groups('GND'),key=len,reverse=True)
for g in gs[1:]:
 tree=STRtree([j.geom for j in r.items])
 pads=[i for i in g if i.kind=='pad'];geom=unary_union([i.geom for i in g]);x0,y0,x1,y1=geom.bounds;best=[]
 for x in np.arange(math.ceil(x0/.1),math.floor(x1/.1)+1)*.1:
  for y in np.arange(math.ceil(y0/.1),math.floor(y1/.1)+1)*.1:
   pt=Point(x,y)
   if not geom.buffer(-.02).covers(pt):continue
   copper=pt.buffer(.3);hole=pt.buffer(.15);hits=[];blocked=False
   for idx in tree.query(pt.buffer(.56)):
    j=r.items[int(idx)]
    if j.net=='GND':continue
    if not ((j.layers and copper.distance(j.geom)<.1271) or (j.hole is not None and hole.distance(j.hole)<.2501) or (j.layers and hole.distance(j.geom)<.2501) or (j.hole is not None and j.hole.distance(copper)<.2501)):continue
    if j.kind not in ('track','via') or j.net in CRITICAL:blocked=True;break
    hits.append(j)
   if blocked:continue
   vip=any(hole.distance(j.geom)<.1 for j in pads)
   score=sum((20 if j.kind=='via' else 1)+(5 if j.net in rb.POWER else 0)+(4 if 'F.Cu' in j.layers else 0) for j in hits)+3*vip
   best.append((score,float(x),float(y),vip,sorted(set(j.net for j in hits)),[j.label for j in hits]))
 best.sort();print([p.label for p in pads],best[:2],flush=True)
 if best and '--apply' in sys.argv:
  _,x,y,*_=best[0];force('GND',[(x,y)]);r=RepairRouter(rb.load(P))
if '--apply' in sys.argv:
 prune();names=list(status());run(names,.025);status()
