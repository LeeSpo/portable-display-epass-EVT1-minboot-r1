#!/usr/bin/env python3
"""Increase power trace width where copper clearance permits; report necks."""
import argparse
import json
from pathlib import Path
from shapely.geometry import LineString
from finish_power_routes import Router,rb
from kicad_sexpr import dumps,children,values

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--report',required=True);opt=ap.parse_args()
    board=rb.load(opt.board);r=Router(board);changes=[]
    main={'VSYS','VBUS','VBAT','3V3','CORE_0V93','DRAM_1V5','1V8'}
    for i in r.items:
        if i.kind!='track' or i.net not in rb.POWER|rb.LX:continue
        old=float(values(i.node,'width')[0]);limit=.60 if i.net in main else .40 if i.net in rb.LX else .30
        for width in [.60,.50,.40,.30,.25,.20,.18]:
            if width<=old+1e-6 or width>limit:continue
            geom=LineString(i.pos).buffer(width/2,quad_segs=16)
            if not r._ok(geom,i.layers,i.net):continue
            node=next(n for n in i.node if isinstance(n,list) and n and n[0]=='width');node[1]=width
            i.geom=geom;r._rebuild_tree()
            changes.append({'net':i.net,'uuid':i.label,'from_mm':old,'to_mm':width});break
    Path(opt.board).write_text(dumps(board)+'\n')
    lengths={}
    for i in r.items:
        if i.kind!='track' or i.net not in main:continue
        w=float(values(i.node,'width')[0]);d=LineString(i.pos).length
        rec=lengths.setdefault(i.net,{'total_mm':0,'below_0p3_mm':0,'minimum_mm':w})
        rec['total_mm']+=d;rec['below_0p3_mm']+=d if w<.30 else 0;rec['minimum_mm']=min(rec['minimum_mm'],w)
    Path(opt.report).write_text(json.dumps({'changed_segments':len(changes),'changes':changes,'trace_lengths':lengths,'ampacity_verified':False},indent=2))
    print('Widened',len(changes),'power segments')

if __name__=='__main__':main()
