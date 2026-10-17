from repair import *
import inspect,numpy as np,shapely
src=inspect.getsource(route).replace('def route(', 'def soft_route(')
src=src.replace('    vg=unary_union', '''    softmask=[]
    for layer in layers:
        sg=unary_union([i.geom.buffer(width/2+.129) for i in r.soft if layer in i.layers])
        softmask.append(shapely.intersects_xy(sg,xx,yy))
    penalty=np.array(softmask,dtype=float)*35
    vg=unary_union''')
src=src.replace("w*(3 if layers[l]=='In2.Cu' else 1)","w*(3 if layers[l]=='In2.Cu' else 1)+penalty[l,ay,ax]")
src=src.replace('1.3/step)', '1.3/step+sum(penalty[:,y,x])*4)')
from route_remaining import heapq
scope=dict(globals());exec(src,scope);soft_route=scope['soft_route']
class Planner(RepairRouter):
 def __init__(self,b,net,locked):
  super().__init__(b)
  self.soft=[i for i in self.items if i.kind in ('track','via') and i.net!=net and i.net not in locked and (i.net!='GND' or i.kind=='via')]
  softids={id(i) for i in self.soft};self.all_items=self.items;self.items=[i for i in self.items if id(i) not in softids];self._rebuild_tree();self.via_xy=[i.pos for i in self.items if i.kind=='via']
 def groups(self,net):return [g for g in connected_groups([i for i in self.all_items+self.zones if i.net==net]) if any(i.kind=='pad' for i in g)]
 def commit_xy(self,pts,width,net):self.path=pts;return True

def negotiate(net,locked,step=.05,width=None):
 b=rb.load(P);r=Planner(b,net,locked);top=net in CRITICAL;r.top_only=top
 if top:r.routing_layers=['F.Cu','B.Cu']
 w=width or (.18 if net in rb.POWER else .127);rec=soft_route(r,net,w,step,top)
 if not rec['ok']:return rec
 rem=set();checks=[]
 for a,c in zip(r.path,r.path[1:]):
  if a[2]!=c[2]:checks.append((Point(a[:2]).buffer(.3),{'F.Cu','B.Cu','In1.Cu','In2.Cu'},Point(a[:2]).buffer(.15)))
  else:checks.append((LineString([a[:2],c[:2]]).buffer(w/2),{a[2]},None))
 for g,ls,h in checks:
  for i in r.soft:
   bad=bool(ls&i.layers) and i.geom.distance(g)<.1271
   bad|=h is not None and i.hole is not None and h.distance(i.hole)<.2501
   bad|=h is not None and bool(i.layers) and h.distance(i.geom)<.2501
   bad|=i.hole is not None and i.hole.distance(g)<.2501
   if bad:rem.add(i.label)
 b=cut(b,rem);rr=RepairRouter(b);ok=rr.commit_xy(r.path,w,net)
 if not ok:return {'ok':False,'reason':'exact validation','path':r.path}
 save(b);rr.write();return {'ok':True,'removed':len(rem),'victims':sorted(set(i.net for i in r.soft if i.label in rem)),'path':r.path}
def batch(nets,locked=None,step=.05):
 locked=set(locked or CRITICAL);report=[]
 for net in nets:
  passes=[]
  for _ in range(20):
   if len(RepairRouter(rb.load(P)).groups(net))<2:break
   rec=negotiate(net,locked,step,.127 if net=='VBAT' else None);passes.append(rec)
   print(net,{k:v for k,v in rec.items() if k!='path'},flush=True)
   if not rec['ok']:break
  done=len(RepairRouter(rb.load(P)).groups(net))<2
  if done:locked.add(net);prune([net])
  report.append({'net':net,'done':done,'passes':passes});(W/'negotiated_latest.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
if __name__=='__main__':batch(sys.argv[1:])
