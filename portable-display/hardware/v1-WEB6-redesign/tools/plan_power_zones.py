#!/usr/bin/env python3
"""Build connected In2 power corridors around through copper and B.Cu references.

Outputs polygons for native KiCad zone creation; does not claim ampacity or SI.
"""
import argparse, heapq, json, math
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from finish_power_routes import Router, rb

STEP=.1
XX,YY=np.meshgrid(np.arange(381)*STEP,np.arange(641)*STEP)
NETS=['DRAM_1V5','1V8','CORE_0V93','VSYS','3V3']

def route(a,b,obstacle):
    blocked=shapely.intersects_xy(obstacle,XX,YY)
    def ends(p):
        x,y=p;ix,iy=round(x/STEP),round(y/STEP);out=[]
        for dx in range(-3,4):
            for dy in range(-3,4):
                nx,ny=ix+dx,iy+dy
                if not(0<nx<380 and 0<ny<640) or blocked[ny,nx]:continue
                if not obstacle.intersects(LineString([p,(nx*STEP,ny*STEP)])):out.append((nx,ny))
        return out
    starts=ends(a);targets=set(ends(b))
    if not starts or not targets:return None
    def h(s):return math.hypot(s[0]-b[0]/STEP,s[1]-b[1]/STEP)
    ds={s:0 for s in starts};parent={};heap=[(h(s),0,s) for s in starts];heapq.heapify(heap);seen=set()
    while heap:
        _,cost,s=heapq.heappop(heap)
        if s in seen:continue
        seen.add(s)
        if s in targets:
            ps=[s]
            while ps[-1] in parent:ps.append(parent[ps[-1]])
            return [a]+[(x*STEP,y*STEP) for x,y in reversed(ps)]+[b]
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            n=(s[0]+dx,s[1]+dy);nx,ny=n
            if not(0<nx<380 and 0<ny<640) or blocked[ny,nx]:continue
            nc=cost+1
            if nc>=ds.get(n,1e20):continue
            ds[n]=nc;parent[n]=s;heapq.heappush(heap,(nc+h(n),nc,n))
    return None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--output',required=True);o=ap.parse_args()
    r=Router(rb.load(o.board));zones=[];occupied=[];report={};seeds={};base={}
    # Keep a ground reference corridor under every existing fast B.Cu segment.
    critical=rb.HS|{'SD_CLK','XIN','XOUT'}
    refs=unary_union([i.geom.buffer(.65) for i in r.items if i.kind=='track' and i.net in critical and 'B.Cu' in i.layers])
    for net in NETS:
        pts=list(dict.fromkeys(i.pos for i in r.items if i.net==net and (i.kind=='via' or i.kind=='pad' and 'In2.Cu' in i.layers)))
        hard=unary_union([r.keep,refs]+occupied+[i.geom.buffer(.18) for i in r.items if i.net!=net and 'In2.Cu' in i.layers])
        pts.sort(key=lambda p:hard.distance(Point(p)),reverse=True)
        paths=[];miss=[];done=pts[:1];pending=pts[1:]
        while pending:
            candidates=sorted((math.dist(a,b),a,b) for a in done for b in pending)
            found=False
            for _,a,b in candidates:
                for width in [.8,.5,.3]:
                    ps=route(a,b,hard.buffer(width/2))
                    if ps:
                        paths.append(LineString(ps).buffer(width/2,join_style=2));done.append(b);pending.remove(b);found=True;break
                if found:break
            if not found:miss.extend(pending);break
        seed=unary_union(paths+[Point(p).buffer(.35) for p in done])
        # Grow the connected trunk into local copper areas, respecting references.
        geom=seed.difference(hard).intersection(box(.5,.5,37.5,63.5))
        polys=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
        kept=[p for p in polys if p.geom_type=='Polygon' and any(p.intersects(Point(q)) for q in done)]
        seeds[net]=unary_union(kept);base[net]=hard
        occupied.append(unary_union(kept).buffer(.18))
        report[net]={'through_points':len(pts),'unreached':miss,'polygons':len(kept),'area_mm2':sum(p.area for p in kept)}
        print(net,report[net],flush=True)
    grown=[]
    for net,seed in seeds.items():
        obstacles=unary_union([base[net]]+grown+[g.buffer(.18) for n,g in seeds.items() if n!=net])
        geom=seed.buffer(.65,join_style=2).difference(obstacles).intersection(box(.5,.5,37.5,63.5))
        polys=[geom] if geom.geom_type=='Polygon' else list(geom.geoms)
        polys=[p.simplify(.005,preserve_topology=True) for p in polys if p.geom_type=='Polygon' and p.intersects(seed)]
        for poly in polys:zones.append({'net':net,'outer':list(poly.exterior.coords)[:-1],'holes':[list(h.coords)[:-1] for h in poly.interiors]})
        grown.append(unary_union(polys).buffer(.18))
        report[net]['area_mm2']=sum(p.area for p in polys)
    Path(o.output).write_text(json.dumps({'zones':zones,'report':report,'reference_margin_mm':.65},indent=2))

if __name__=='__main__':main()
