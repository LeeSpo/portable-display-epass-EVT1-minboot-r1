#!/usr/bin/env python3
"""Route local bridges on In2; In1 is never offered as a signal layer."""
import argparse,json,time
from pathlib import Path
from finish_power_routes import Router,rb
from plane_connectivity import zones
from route_remaining import route

class BridgeRouter(Router):
    routing_layers=['F.Cu','B.Cu','In2.Cu']
    def endpoints(self,g):
        pts=[]
        for i in g:
            if i.kind=='pad':pts.extend((*i.pos,l) for l in i.layers&set(self.routing_layers))
            elif i.kind=='via':pts.extend((*i.pos,l) for l in self.routing_layers)
            elif i.kind=='track':pts.extend((*p,next(iter(i.layers))) for p in i.pos)
        return list(set(pts))

ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('nets',nargs='+');ap.add_argument('--avoid-power',action='store_true');ap.add_argument('--step',type=float,default=.05);ap.add_argument('--report',required=True);args=ap.parse_args()
rb.BOARD=Path(args.board);report=[]
for net in args.nets:
    b=rb.load(args.board);r=BridgeRouter(b)
    if args.avoid_power:r.items.extend(z for z in zones(b) if z.net!='GND' and 'In2.Cu' in z.layers);r._rebuild_tree()
    t=time.time();recs=[]
    for attempt in range(10):
        rec=route(r,net,.127,args.step);recs.append(rec)
        if not rec['ok'] or len(r.groups(net))<2:break
    if r.added:r.write()
    rec={'net':net,'ok':len(r.groups(net))<2,'groups':len(r.groups(net)),'routes':recs,'seconds':round(time.time()-t,2)}
    report.append(rec);Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
    print(net,rec['ok'],rec['groups'],r.report['added_tracks'],r.report['added_vias'],rec['seconds'],recs[-1].get('reason'),flush=True)
