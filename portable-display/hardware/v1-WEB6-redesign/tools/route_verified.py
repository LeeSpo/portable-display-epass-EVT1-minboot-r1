#!/usr/bin/env python3
"""Route corrected footprints while respecting the MEMS component exclusion areas."""
import argparse,json,uuid
from pathlib import Path
from shapely.geometry import box,Polygon
from shapely.ops import unary_union
from finish_power_routes import Router,rb
from plane_connectivity import children,values,val,dumps,zones,connected_groups
from route_remaining import route
class VerifiedRouter(Router):
    def _ok(self,geom,layers,net,hole=None):
        if 'F.Cu' in layers and geom.intersects(box(8.9,5.4,10.1,6.6)):return False
        if hole is not None and geom.intersects(box(8.45,4.95,10.55,7.05)):return False
        return super()._ok(geom,layers,net,hole)
    def _obstacles(self,net,width,layer):
        obs=super()._obstacles(net,width,layer)
        if layer=='F.Cu':obs=unary_union([obs,box(8.9,5.4,10.1,6.6).buffer(width/2)])
        if abs(width-.6)<1e-9:obs=unary_union([obs,box(8.45,4.95,10.55,7.05).buffer(.3)])
        return obs

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('nets',nargs='*');ap.add_argument('--top-only',action='store_true');ap.add_argument('--width',type=float,default=.127);ap.add_argument('--step',type=float,default=.05);ap.add_argument('--report',required=True);ap.add_argument('--u4-escape',action='store_true');a=ap.parse_args();rb.BOARD=Path(a.board);r=VerifiedRouter(rb.load(a.board));report=[]
    if a.u4_escape:
        fan={1:[(8.7375,5.25),(8.25,5.25)],2:[(8.7375,5.75),(8.25,5.75)],4:[(8.7375,6.75),(8.25,6.75)],6:[(9.75,6.7625),(9.75,7.3),(10,7.55),(11.1696,7.55)],7:[(10.2625,6.75),(10.7,6.75),(11.1696,7.2196),(11.1696,7.55)],8:[(10.2625,6.25),(11.3,6.25),(11.8,6.75),(11.8,7.55),(11.1696,7.55)],9:[(10.2625,5.75),(10.8,5.75)],10:[(10.2625,5.25),(10.8,5.25),(10.8,5.75)],12:[(9.25,5.2375),(9.25,4.6)]}
        for pin,pts in fan.items():
            pad=next(i for i in r.items if i.ref=='U4' and str(i.pin)==str(pin));ok=r.commit_xy([(*p,'F.Cu') for p in pts],.127,pad.net);report.append({'pin':pin,'fanout':ok});print(report[-1],flush=True)
    for net in a.nets:
        r.top_only=a.top_only;passes=[]
        for _ in range(20):
            rec=route(r,net,a.width,a.step,a.top_only);passes.append(rec)
            if not rec['ok'] or len(r.groups(net))<2:break
        report.append({'net':net,'passes':passes,'groups':len(r.groups(net))});print(net,passes[-1]['ok'],len(r.groups(net)),flush=True)
    r.write();Path(a.report).write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
