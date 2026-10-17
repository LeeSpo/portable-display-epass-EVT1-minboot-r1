#!/usr/bin/env python3
"""Geometry-checked routing for the power placement candidate (Shapely 2).

Uses real copper connectivity, checks full via clearance before layer changes,
and coalesces grid steps. Native KiCad DRC remains the acceptance test.
"""
import argparse
import heapq
import json
import math
import sys
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
import route_board as rb
from geometry_audit import connected_groups, issues

STEP = .10
X, Y = np.meshgrid(np.arange(381)*STEP, np.arange(641)*STEP)


class Router(rb.Router):
    def __init__(self, board):
        super().__init__(board)
        self.ids = {i.net: rb.q(i.net) for i in self.items if i.net}
        self.via_xy = [i.pos for i in self.items if i.kind == 'via']
        self._rebuild_tree()

    def commit_xy(self, pts, width, net):
        out = []
        for p in pts:
            if out and p == out[-1]: continue
            if len(out)>1 and p[2] == out[-1][2] == out[-2][2]:
                a,b=out[-2:]
                if abs((b[0]-a[0])*(p[1]-b[1])-(b[1]-a[1])*(p[0]-b[0])) < 1e-8:
                    out.pop()
            out.append(p)
        return super().commit_xy(out,width,net)

    def astar(self, a, b, width, net):
        if getattr(self,'top_only',False) and (a[2]!='F.Cu' or b[2]!='F.Cu'):return False
        layers=['F.Cu','B.Cu']
        obs=[self._obstacles(net,width,l) for l in layers]
        block=np.array([shapely.intersects_xy(g,X,Y) for g in obs])
        vg=unary_union([self._obstacles(net,.6,l) for l in layers])
        via=~shapely.intersects_xy(vg,X,Y)
        if getattr(self,'top_only',False):via[:]=False;block[1,:,:]=True
        for vx,vy in self.via_xy: via &= (X-vx)**2+(Y-vy)**2 >= .73**2
        # Exact endpoint to nearby grid connection, checked geometrically.
        def endpoints(pt):
            x,y,l=pt; li=layers.index(l); out=[]
            ix,iy=round(x/STEP),round(y/STEP)
            for dx in range(-2,3):
                for dy in range(-2,3):
                    nx,ny=ix+dx,iy+dy
                    if not (0<=nx<381 and 0<=ny<641) or block[li,ny,nx]:continue
                    p=(nx*STEP,ny*STEP)
                    g=LineString([(x,y),p]).buffer(width/2)
                    if self._ok(g,frozenset([l]),net):out.append((li,ny,nx))
            return out
        starts,targets=endpoints(a),set(endpoints(b))
        if not starts or not targets:return False
        tx,ty=b[:2]
        def h(s):return abs(s[2]-tx/STEP)+abs(s[1]-ty/STEP)
        dist={s:0 for s in starts};parent={};heap=[(h(s),0,s) for s in starts];heapq.heapify(heap);seen=set();end=None
        while heap and len(seen)<140000:
            _,cost,s=heapq.heappop(heap)
            if s in seen:continue
            seen.add(s)
            if s in targets:end=s;break
            l,y,x=s
            neighbors=[((l,y+dy,x+dx),1) for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]]
            if via[y,x]:neighbors.append(((1-l,y,x),18))
            for ns,w in neighbors:
                nl,ny,nx=ns
                if not(0<=nx<381 and 0<=ny<641) or block[nl,ny,nx]:continue
                nc=cost+w
                if nc>=dist.get(ns,1e20):continue
                dist[ns]=nc;parent[ns]=s;heapq.heappush(heap,(nc+h(ns),nc,ns))
        if end is None:return False
        path=[end]
        while path[-1] in parent:path.append(parent[path[-1]])
        path.reverse()
        return self.commit_xy([a]+[(x*STEP,y*STEP,layers[l]) for l,y,x in path]+[b],width,net)

    def groups(self,net):
        return [g for g in connected_groups([i for i in self.items if i.net==net])
                if any(i.kind=='pad' for i in g)]

    def endpoints(self,g):
        pts=[]
        for i in g:
            if i.kind=='pad':
                for l in i.layers & {'F.Cu','B.Cu'}:pts.append((*i.pos,l))
            elif i.kind=='via':
                pts.extend([(*i.pos,'F.Cu'),(*i.pos,'B.Cu')])
            else:
                for p in i.pos:pts.append((*p,next(iter(i.layers))))
        return list(set(p for p in pts if not getattr(self,'top_only',False) or p[2]=='F.Cu'))

    def complete(self, net, width):
        failed=set()
        for iteration in range(60):
            gs=self.groups(net)
            if len(gs)<2:return True
            pairs=[]
            for i,g in enumerate(gs):
                aa=self.endpoints(g)
                for gg in gs[i+1:]:
                    bb=self.endpoints(gg)
                    for la,lb in [('B.Cu','B.Cu'),('F.Cu','F.Cu'),('F.Cu','B.Cu'),('B.Cu','F.Cu')]:
                        penalty=0 if la==lb=='B.Cu' else 6 if la==lb else 10
                        cands=sorted((math.dist(a[:2],b[:2])+penalty,a,b) for a in aa if a[2]==la for b in bb if b[2]==lb)
                        pairs.extend(cands[:4])
            ok=False
            for d,a,b in sorted(pairs):
                if (a,b) in failed:continue
                if a[2]==b[2] and self.manhattan(*a[:2],*b[:2],a[2],width,net):ok=True;break
                if self.astar(a,b,width,net):ok=True;break
                failed.add((a,b))
                if len(failed)>80:return False
            if not ok:return False
        return False

    def escape_power(self):
        # Short fine necks only at the fine-pitch SoC, followed by wider copper.
        for i in list(self.items):
            if i.kind!='pad' or i.ref!='U2' or i.net not in rb.POWER:continue
            x,y=i.pos
            dx,dy=((1,0) if x>22 else (-1,0) if x<14 else (0,-1) if y<24 else (0,1))
            for length in [.8,1.0,1.2,1.4,1.6]:
                px,py=x+dx*length,y+dy*length
                if self.add_seg(x,y,px,py,.18,'F.Cu',i.net):break

    def inner_power_vias(self):
        # Ordinary through vias inside the SoC perimeter, outside its exposed pad.
        # Stagger radial distances so adjacent fine-pitch pins do not need tiny holes.
        pads=[i for i in self.items if i.kind=='pad' and i.ref=='U2' and i.net in rb.POWER]
        pads.sort(key=lambda p:int(p.pin))
        for i in pads:
            x,y=i.pos
            dx,dy=((-1,0) if x>22 else (1,0) if x<14 else (0,1) if y<24 else (0,-1))
            for length in [.8,1.6,2.4,1.0,1.8,2.2]:
                px,py=x+dx*length,y+dy*length
                if self.commit_xy([(x,y,'F.Cu'),(px,py,'F.Cu'),(px,py,'B.Cu')],.18,i.net):break
