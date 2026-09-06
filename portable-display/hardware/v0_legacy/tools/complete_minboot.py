#!/usr/bin/env python3
"""Close remaining minboot islands on an existing, natively filled board.

Routes only F.Cu/B.Cu, preserving the ground reference layer. Native KiCad
refill/DRC remains authoritative. Default writes a candidate, never the source.
"""
import argparse, heapq, json, math, uuid
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from geometry_audit import Item, board_items, connected_groups, issues
from kicad_sexpr import load, dump, children, child, val, values, Q
from route_minboot import Router, width_for
from check_minboot import DISPLAY_NETS

LAYERS = ('F.Cu', 'B.Cu')
STEP = .15
ORIGIN = .75
NX, NY = int((57.25-ORIGIN)/STEP)+1, int((109.25-ORIGIN)/STEP)+1

def filled_items(board):
    result=[]
    for z in children(board,'zone'):
        net=str(val(z,'net_name',val(z,'net')))
        for p in children(z,'filled_polygon'):
            pts=child(p,'pts',[])
            coords=[(float(q[1]),float(q[2])) for q in pts[1:] if q[0]=='xy']
            if len(coords)<3:continue
            geom=shapely.make_valid(Polygon(coords))
            result.append(Item('zone',net,frozenset((str(val(p,'layer',val(z,'layer'))),)),geom,z,'zone',pos=()))
    return result

class Closure(Router):
    def __init__(self,board,filled):
        super().__init__(board)
        self.zones=filled_items(filled)
        self.serial=uuid.uuid4().hex[:10]

    def obstacles(self,net,width):
        obs=[[],[]]; vh=[]
        for it in self.items:
            same=it.net==net
            if not same:
                for l,layer in enumerate(LAYERS):
                    if layer in it.layers:obs[l].append(it.geom.buffer(.092+width/2))
                if it.layers:vh.append(it.geom.buffer(max(.202+.092,.102+.252)))
                if it.hole is not None:
                    for l in range(2):obs[l].append(it.hole.buffer(.252+width/2))
            if it.hole is not None:vh.append(it.hole.buffer(.252+.102))
        # Existing keepouts must also be honored.
        for z in children(self.board,'zone'):
            ko=child(z,'keepout')
            if ko is None:continue
            pts=child(child(z,'polygon',[]),'pts',[])
            poly=Polygon([(float(q[1]),float(q[2])) for q in pts[1:]])
            ls=values(z,'layers') or values(z,'layer')
            if str(val(ko,'tracks'))=='not_allowed':
                for l,layer in enumerate(LAYERS):
                    if layer in ls:obs[l].append(poly.buffer(width/2))
            if str(val(ko,'vias'))=='not_allowed':vh.append(poly.buffer(.202))
        self.obs=[unary_union(x) for x in obs];self.vobs=unary_union(vh)
        for p in self.obs+[self.vobs]:shapely.prepare(p)
        ys,xs=np.mgrid[0:NY,0:NX];xx=ORIGIN+xs*STEP;yy=ORIGIN+ys*STEP
        self.block=np.array([shapely.intersects_xy(p.buffer(STEP*.71),xx,yy) for p in self.obs])
        self.vblock=shapely.intersects_xy(self.vobs,xx,yy)
        return xx,yy

    def anchors(self,g):
        anchors=[]
        for it in g:
            if it.kind=='zone':
                if not getattr(self,'zone_anchors',False):continue
                minx,miny,maxx,maxy=it.geom.bounds
                pts=[(float(x),float(y)) for x in np.arange(minx+.2,maxx,1.2) for y in np.arange(miny+.2,maxy,1.2) if it.geom.contains(Point(x,y))]
                for p in pts:
                    for l,layer in enumerate(LAYERS):
                        if layer in it.layers:anchors.append((*p,l))
                continue
            if it.kind=='track':
                a,b=it.pos;dist=math.dist(a,b);n=max(1,int(dist/1.5))
                pts=[(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n) for i in range(n+1)]
            else:pts=[it.pos]
            for p in pts:
                for l,layer in enumerate(LAYERS):
                    if layer in it.layers:anchors.append((float(p[0]),float(p[1]),l))
        return list(dict.fromkeys(anchors))

    def seeds(self,anchors):
        seeds={}
        for x,y,l in anchors:
            ix,iy=round((x-ORIGIN)/STEP),round((y-ORIGIN)/STEP)
            opts=[]
            for dy in range(-6,7):
                for dx in range(-6,7):
                    jx,jy=ix+dx,iy+dy
                    if not(0<=jx<NX and 0<=jy<NY) or self.block[l,jy,jx]:continue
                    px,py=ORIGIN+jx*STEP,ORIGIN+jy*STEP
                    dist=math.hypot(px-x,py-y)
                    opts.append((dist,jx,jy,px,py))
            count=0
            for dist,jx,jy,px,py in sorted(opts):
                if shapely.intersects(self.obs[l],LineString([(x,y),(px,py)])):continue
                k=(l,jy,jx)
                if k not in seeds or dist<seeds[k][0]:seeds[k]=(dist,(x,y,l))
                count+=1
                if count>=8:break
        return seeds

    def join(self,net,src,dst,width):
        starts=self.seeds(self.anchors(src));goals=self.seeds(self.anchors(dst))
        if not starts or not goals:
            print('no terminal access',len(starts),len(goals),flush=True);return False
        coords=np.array([(k[2],k[1]) for k in goals]); xmin,ymin=coords.min(axis=0);xmax,ymax=coords.max(axis=0)
        def h(k):
            l,y,x=k
            return math.hypot(max(xmin-x,0,x-xmax),max(ymin-y,0,y-ymax))*STEP
        dist={k:v[0] for k,v in starts.items()};parents={};heap=[(v+h(k),v,k) for k,v in dist.items()];heapq.heapify(heap);done=set();end=None
        while heap:
            _,cost,k=heapq.heappop(heap)
            if k in done:continue
            done.add(k)
            if k in goals:end=k;break
            l,y,x=k
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1),(0,0)):
                nl,ny,nx=(1-l,y,x) if dx==dy==0 else (l,y+dy,x+dx)
                if not(0<=nx<NX and 0<=ny<NY) or self.block[nl,ny,nx]:continue
                if nl!=l and self.vblock[y,x]:continue
                nk=(nl,ny,nx)
                if nk in done:continue
                nc=cost+(2.5 if nl!=l else STEP*math.hypot(dx,dy))
                if nc>=dist.get(nk,float('inf')):continue
                dist[nk]=nc;parents[nk]=k;heapq.heappush(heap,(nc+h(nk),nc,nk))
        if end is None:
            print('no grid path',len(done),flush=True);return False
        path=[end]
        while path[-1] in parents:path.append(parents[path[-1]])
        path.reverse()
        points=[starts[path[0]][1]]+[(ORIGIN+x*STEP,ORIGIN+y*STEP,l) for l,y,x in path]+[goals[end][1]]
        # Remove collinear lattice steps, retaining exact pad/track endpoints.
        merged=[]
        for p in points:
            if merged and math.dist(p,merged[-1])<1e-8:continue
            while len(merged)>1:
                a,b=merged[-2:]
                if a[2]!=b[2] or b[2]!=p[2]:break
                if abs((b[0]-a[0])*(p[1]-b[1])-(b[1]-a[1])*(p[0]-b[0]))>1e-7:break
                merged.pop()
            merged.append(p)
        pieces=[]
        for n,(a,b) in enumerate(zip(merged,merged[1:])):
            tag=f'closure-{self.serial}-{net}-{self.report["added_tracks"]}-{n}'
            if a[2]!=b[2]:pieces.append(('via',(a[0],a[1],net,tag)))
            else:
                if shapely.intersects(self.obs[a[2]],LineString([a[:2],b[:2]])):
                    print('invalid segment',a,b,flush=True);return False
                pieces.append(('seg',(*a[:2],*b[:2],width,LAYERS[a[2]],net,tag)))
        ok=self.commit(pieces)
        if not ok:print('commit rejected',len(pieces),flush=True)
        return ok

    def close(self,net):
        width=width_for(net)
        for iteration in range(50):
            groups=[g for g in connected_groups([i for i in self.items+self.zones if i.net==net]) if any(i.kind=='pad' for i in g)]
            if len(groups)<=1:return True
            print(net,'islands',len(groups),flush=True)
            self.obstacles(net,width)
            pairs=sorted((min(a.geom.distance(b.geom) for a in g if a.kind=='pad' for b in h if b.kind=='pad'),j,k) for j,g in enumerate(groups) for k,h in enumerate(groups) if j<k)
            for _,j,k in pairs:
                if self.join(net,groups[j],groups[k],width):break
            else:
                if not getattr(self,'zone_anchors',False):
                    self.zone_anchors=True
                    continue
                return False
        return False

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--nets',required=True);p.add_argument('--filled',type=Path,required=True);a=p.parse_args()
    b=load(a.input);r=Closure(b,load(a.filled));result={}
    for net in a.nets.split(','):
        if net in DISPLAY_NETS:raise ValueError('Display net outside minboot scope')
        result[net]=r.close(net);print(net,result[net],flush=True)
        # Save progress only to the requested candidate.
        r._strip_zone_fills();dump(b,a.output)
    errors=issues(board_items(b))
    a.output.with_suffix('.routing.json').write_text(json.dumps({'nets':result,'tracks_added':r.report['added_tracks'],'vias_added':r.report['added_vias'],'geometry_issues':errors},indent=2))
    print('geometry issues',len(errors),flush=True)
if __name__=='__main__':main()
