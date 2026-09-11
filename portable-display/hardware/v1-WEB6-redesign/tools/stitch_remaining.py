#!/usr/bin/env python3
"""Stitch ground islands containing pads, using native saved zone geometry."""
import argparse,json
from pathlib import Path
import numpy as np
import shapely
from shapely.ops import unary_union
from shapely.geometry import Point
from finish_power_routes import Router,rb
from plane_connectivity import zones,connected_groups
from route_remaining import route
ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--report',required=True);args=ap.parse_args()
rb.BOARD=Path(args.board);r=Router(rb.load(args.board));zs=zones(r.board)
gs=connected_groups([i for i in r.items+zs if i.net=='GND']);gs.sort(key=len,reverse=True)
report=[]
for group in gs[1:]:
    pads=[i for i in group if i.kind=='pad'];polys=[i.geom for i in group if i.kind=='zone']
    if not pads:continue
    geom=unary_union(polys+[i.geom for i in pads]);x0,y0,x1,y1=geom.bounds
    xx,yy=np.meshgrid(np.arange(np.ceil(x0/.05),np.floor(x1/.05)+1)*.05,np.arange(np.ceil(y0/.05),np.floor(y1/.05)+1)*.05)
    mask=shapely.intersects_xy(geom.buffer(-.02),xx,yy)
    cands=list(zip(xx[mask],yy[mask]));cands.sort(key=lambda q:min((q[0]-p.pos[0])**2+(q[1]-p.pos[1])**2 for p in pads))
    ok=False
    for x,y in cands:
        # Keep plated drills out of SMD solder lands; connect through surrounding copper.
        hole=Point(float(x),float(y)).buffer(.15)
        if any(hole.distance(i.geom)<.1 for i in r.items if i.kind=='pad'):continue
        if r.add_via(float(x),float(y),'GND'):
            rec={'pads':[p.label for p in pads],'ok':True,'via':[float(x),float(y)]};ok=True;break
    if not ok:
        r.groups=lambda net:[group,gs[0]]
        rec=route(r,'GND',.127,.05);rec['pads']=[p.label for p in pads]
    report.append(rec);print({k:v for k,v in rec.items() if k!='path'},flush=True)
r.write();Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
