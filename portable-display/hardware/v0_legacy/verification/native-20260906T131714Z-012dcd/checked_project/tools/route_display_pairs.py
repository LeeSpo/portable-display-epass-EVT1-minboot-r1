#!/usr/bin/env python3
"""Candidate MIPI coupled F.Cu routes above In1 ground; native DRC required.

0.09mm width / 0.09mm edge gap are geometric candidates, NOT an impedance
specification. Actual stackup, skew budget and return-path signoff remain open.
Both traces are committed atomically; failures leave the pair absent.
"""
import argparse,heapq,json,math
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import LineString,Point
from shapely.ops import unary_union
from kicad_sexpr import load,dump
from route_minboot import Router
from geometry_audit import issues

W=.09;GAP=.09;OFFSET=(W+GAP)/2;STEP=.05

def pair(r,name,sx,tx,layer="F.Cu",source_y=50.4,target_y=40.6):
    nets=['DSI_'+name+'P','DSI_'+name+'N']
    obs=[]
    for i in r.items:
        if i.net in nets:continue
        if layer in i.layers:obs.append(i.geom.buffer(.092+(2*W+GAP)/2))
        if i.hole is not None:obs.append(i.hole.buffer(.252+(2*W+GAP)/2))
    poly=unary_union(obs);shapely.prepare(poly)
    x0,y0=18.,35.;nx,ny=700,340
    yy,xx=np.mgrid[0:ny,0:nx];block=shapely.intersects_xy(poly.buffer(STEP*.71),x0+xx*STEP,y0+yy*STEP)
    def cell(x,y):return(round((x-x0)/STEP),round((y-y0)/STEP))
    def xy(k):return(x0+k[0]*STEP,y0+k[1]*STEP)
    start=cell(sx,source_y-.3);goal=cell(tx,target_y+.3)
    if block[start[1],start[0]] or block[goal[1],goal[0]]:print(name,'blocked pair access',flush=True);return False
    dist={start:0};parent={};heap=[(math.dist(start,goal)*STEP,0,start)];done=set();end=None
    while heap:
        _,c,k=heapq.heappop(heap)
        if k in done:continue
        done.add(k)
        if k==goal:end=k;break
        for dx,dy in [(0,-1),(1,0),(-1,0),(0,1),(1,-1),(-1,-1),(1,1),(-1,1)]:
            nk=(k[0]+dx,k[1]+dy)
            if not(0<=nk[0]<nx and 0<=nk[1]<ny) or block[nk[1],nk[0]] or nk in done:continue
            nc=c+math.hypot(dx,dy)*STEP
            if nc>=dist.get(nk,1e9):continue
            dist[nk]=nc;parent[nk]=k;heapq.heappush(heap,(nc+math.dist(nk,goal)*STEP,nc,nk))
    if end is None:print(name,'no paired corridor',len(done),flush=True);return False
    path=[end]
    while path[-1] in parent:path.append(parent[path[-1]])
    path.reverse();points=[(sx,source_y)]+[xy(k) for k in path]+[(tx,target_y)]
    merged=[]
    for p in points:
        if merged and math.dist(p,merged[-1])<1e-8:continue
        while len(merged)>1:
            a,b=merged[-2:]
            if abs((b[0]-a[0])*(p[1]-b[1])-(b[1]-a[1])*(p[0]-b[0]))>1e-8:break
            merged.pop()
        merged.append(p)
    line=LineString(merged);pieces=[];lengths={}
    for net,sign in zip(nets,[-1,1]):
        curve=line.offset_curve(sign*OFFSET,join_style='mitre')
        if curve.geom_type!='LineString':return False
        pts=list(curve.coords)
        if math.dist(pts[0],(sx+sign*OFFSET,source_y))>.0001 or math.dist(pts[-1],(tx+sign*OFFSET,target_y))>.0001:return False
        pieces += [('seg',(*a,*b,W,layer,net,'mipi-pair-'+str(j))) for j,(a,b) in enumerate(zip(pts,pts[1:]))]
        lengths[net]=curve.length
    ok=r.commit(pieces);print(name,'paired route',ok,lengths,flush=True)
    return {'committed':ok,'trunk_length_mm':lengths,'centerline':merged}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    b=load(a.input);r=Router(b);result={}
    for name,sx,tx in [('CK',27.55,34.95),('D0',28.95,33.75)]:result[name]=pair(r,name,sx,tx)
    r._strip_zone_fills();dump(b,a.output)
    result['geometry_issues']=issues(r.items);result['impedance_verified']=False;result['fabrication_released']=False
    a.output.with_suffix('.pairs.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
