#!/usr/bin/env python3
"""Escape isolated fine-pitch pins, ripping only conflicting trace segments.

Pads, existing vias and screw keepouts are hard obstacles. All new vias remain
0.60/0.30 mm. Removed segments are recorded and must be reconnected afterwards.
"""
import argparse
import json
import math
from pathlib import Path
from shapely.geometry import Point,LineString
from shapely.strtree import STRtree
from finish_power_routes import Router,rb
from kicad_sexpr import dumps,val

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--report',required=True);ap.add_argument('--all-signals',action='store_true');ap.add_argument('--allow-via-ripup',action='store_true');ap.add_argument('--protect-critical',action='store_true');opt=ap.parse_args()
    protected=rb.HS|rb.LX|{'XIN','XOUT','SD_CLK'} if opt.protect_critical else set()
    rb.BOARD=Path(opt.board);r=Router(rb.load(opt.board));result=[]
    todo=[]
    for i in r.items:
        if i.kind!='pad' or not i.net or i.net.startswith('unconnected') or i.net=='GND':continue
        if i.ref not in ['U1','U2','U10']:continue
        if i.net in protected:continue
        if not opt.all_signals and i.net not in rb.POWER and i.net not in ['XIN','XOUT']:continue
        groups=r.groups(i.net)
        if len(groups)<2:continue
        g=next(g for g in groups if i in g)
        if sum(j.kind=='pad' for j in g)>1 or any(j.kind=='via' for j in g):continue
        todo.append((i.net,i.ref,i.pin))
    for net,ref,pin in todo:
        r=Router(rb.load(opt.board));i=next(i for i in r.items if i.ref==ref and i.pin==pin)
        x,y=i.pos
        cx,cy={'U1':(25,50.5),'U2':(18,28),'U10':(7.5,48.7)}[ref]
        dx,dy=((1 if x>cx else -1,0) if abs(x-cx)>abs(y-cy) else (0,1 if y>cy else -1))
        fixed=[j for j in r.items if j.kind=='pad' or j.net in protected or j.kind=='via' and (not opt.allow_via_ripup or j.net==net)]
        checker=Router(rb.load(opt.board));checker.items=fixed;checker._rebuild_tree()
        candidates=[]
        for sign in [1,-1]:
            for length in [.8,1.2,1.6,2.,2.4,2.8,3.2,3.6,4.0]:
                for tangent in [0,.6,-.6,1.2,-1.2,1.8,-1.8,2.4,-2.4,3.0,-3.0,3.6,-3.6]:
                    ex,ey=x+dx*sign*.55,y+dy*sign*.55
                    vx,vy=x+dx*sign*length-dy*tangent,y+dy*sign*length+dx*tangent
                    if any(j.kind=='via' and (not opt.allow_via_ripup or j.net==net) and math.hypot(vx-j.pos[0],vy-j.pos[1])<.73 for j in r.items):continue
                    via=Point(vx,vy).buffer(.3);hole=Point(vx,vy).buffer(.15)
                    segments=[LineString([(x,y),(ex,ey)]).buffer(.127/2),LineString([(ex,ey),(vx,vy)]).buffer(.127/2)]
                    if not checker._ok(via,frozenset(['F.Cu','B.Cu','In1.Cu','In2.Cu']),net,hole):continue
                    if not all(checker._ok(g,frozenset(['F.Cu']),net) for g in segments):continue
                    blockers={j.label for j in r.items if j.kind=='track' and j.net!=net and
                              (j.geom.distance(via)<.127-1e-6 or ('F.Cu' in j.layers and any(j.geom.distance(g)<.127-1e-6 for g in segments)))}
                    via_blockers={j.label for j in r.items if opt.allow_via_ripup and j.kind=='via' and j.net!=net and
                                  (math.hypot(vx-j.pos[0],vy-j.pos[1])<.73 or any(j.geom.distance(g)<.127 for g in segments))}
                    cost=4*len(blockers)+20*len(via_blockers)+length+abs(tangent)
                    blockers |= via_blockers
                    candidates.append((cost,blockers,[(x,y,'F.Cu'),(ex,ey,'F.Cu'),(vx,vy,'F.Cu'),(vx,vy,'B.Cu')]))
        if not candidates:
            result.append({'ref':ref,'pin':pin,'net':net,'unresolved':True});continue
        _,remove,path=min(candidates,key=lambda c:c[0]);tree=rb.load(opt.board)
        removed=[{'uuid':j.label,'net':j.net,'kind':j.kind} for j in r.items if j.label in remove]
        tree=[n for n in tree if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'uuid')) in remove)]
        trial=Router(tree)
        if not trial.commit_xy(path,.127,net):
            result.append({'ref':ref,'pin':pin,'net':net,'unresolved':True});continue
        Path(opt.board).write_text(dumps(tree)+'\n');trial.write()
        result.append({'ref':ref,'pin':pin,'net':net,'via':path[-1][:2],'removed_segments':removed})
        print(ref,pin,net,'escaped; removed',len(remove),flush=True)
    Path(opt.report).write_text(json.dumps(result,indent=2))

if __name__=='__main__':main()
