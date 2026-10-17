#!/usr/bin/env python3
"""Add short checked GND connections to 0.60/0.30 mm plane vias."""
import argparse
import json
import math
from pathlib import Path
from shapely.geometry import Point
from finish_power_routes import Router,rb

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--report',required=True);opt=ap.parse_args()
    rb.BOARD=Path(opt.board);r=Router(rb.load(opt.board));result=[]
    for g in r.groups('GND'):
        if any(i.kind=='via' or i.kind=='pad' and 'B.Cu' in i.layers for i in g):continue
        pads=sorted([i for i in g if i.kind=='pad'],key=lambda p:p.geom.area,reverse=True)
        ok=False
        for p in pads:
            x,y=p.pos
            # Keep new drill holes out of solderable pad area, including EPs.
            candidates=[]
            for radius in [.65,.8,1.0,1.2,1.5,1.8,2.1,2.4]:
                for angle in range(0,360,30):
                    px=round(x+radius*math.cos(math.radians(angle)),3)
                    py=round(y+radius*math.sin(math.radians(angle)),3)
                    candidates.append((px,py))
            if p.pin in ['41','89','13'] and p.ref in ['U1','U2','U10']:
                minx,miny,maxx,maxy=p.geom.bounds
                candidates=[(minx-.5,y),(maxx+.5,y),(x,miny-.5),(x,maxy+.5)]+candidates
            for px,py in candidates:
                hole=Point(px,py).buffer(.15)
                if any(i.kind=='pad' and i.geom.distance(hole)<.1 for i in r.items):continue
                if r.commit_xy([(x,y,'F.Cu'),(px,py,'F.Cu'),(px,py,'B.Cu')],.18,'GND'):
                    result.append({'pads':[i.label for i in pads],'via':[px,py]});ok=True;break
            if ok:break
        if not ok:result.append({'pads':[i.label for i in pads],'unresolved':True})
    r.write()
    Path(opt.report).write_text(json.dumps(result,indent=2))
    print('Ground groups:',len(result),'unresolved:',sum(bool(x.get('unresolved')) for x in result),flush=True)

if __name__=='__main__':main()
