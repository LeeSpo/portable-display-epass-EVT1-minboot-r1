#!/usr/bin/env python3
"""Fine-grid, multi-terminal routing. Native DRC is required after every batch."""
import argparse
import heapq
import json
import math
import time
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from finish_power_routes import Router, rb


def route(r, net, width=.127, step=.05, top_only=False):
    groups=r.groups(net)
    if len(groups)<2:return {'ok':True,'already':True}
    groups.sort(key=len)
    source=groups[0]
    target=[i for g in groups[1:] for i in g]
    layers=getattr(r,'routing_layers',['F.Cu','B.Cu'])
    nx,ny=round(38/step)+1,round(64/step)+1
    xx,yy=np.meshgrid(np.arange(nx)*step,np.arange(ny)*step)
    obs=[r._obstacles(net,width,l) for l in layers]
    block=np.array([shapely.intersects_xy(g,xx,yy) for g in obs])
    vg=unary_union([r._obstacles(net,.6,l) for l in layers])
    via=~shapely.intersects_xy(vg,xx,yy)
    for x,y in r.via_xy:via &= (xx-x)**2+(yy-y)**2>=.73**2
    if top_only:via[:]=False;block[1,:,:]=True
    def term_grid(items):
        result={}
        for p in r.endpoints(items):
            if p[2] not in layers:continue
            li=layers.index(p[2]);ix=round(p[0]/step);iy=round(p[1]/step)
            for dy in range(-2,3):
                for dx in range(-2,3):
                    x,y=ix+dx,iy+dy
                    if not(0<=x<nx and 0<=y<ny) or block[li,y,x]:continue
                    if r._ok(LineString([p[:2],(x*step,y*step)]).buffer(width/2),frozenset([p[2]]),net):
                        result[(li,y,x)]=p
        return result
    starts,ends=term_grid(source),term_grid(target)
    if not starts or not ends:return {'ok':False,'reason':'no grid endpoint','starts':len(starts),'ends':len(ends)}
    tx0,tx1=min(s[2] for s in ends),max(s[2] for s in ends)
    ty0,ty1=min(s[1] for s in ends),max(s[1] for s in ends)
    def heuristic(s):return math.hypot(max(tx0-s[2],s[2]-tx1,0),max(ty0-s[1],s[1]-ty1,0))
    dist={s:0 for s in starts};parent={};heap=[(heuristic(s),0,s) for s in starts];heapq.heapify(heap)
    seen=set();end=None
    dirs=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,1.4142136),(-1,1,1.4142136),(1,-1,1.4142136),(-1,-1,1.4142136)]
    while heap and len(seen)<1800000:
        _,cost,s=heapq.heappop(heap)
        if s in seen:continue
        seen.add(s)
        if s in ends:end=s;break
        l,y,x=s
        neighbors=[]
        for dx,dy,w in dirs:
            ax,ay=x+dx,y+dy
            if not(0<=ax<nx and 0<=ay<ny) or block[l,ay,ax]:continue
            if dx and dy and (block[l,y,ax] or block[l,ay,x]):continue
            neighbors.append(((l,ay,ax),w*(3 if layers[l]=='In2.Cu' else 1)))
        if via[y,x]:
            neighbors.extend(((nl,y,x),1.3/step) for nl in range(len(layers)) if nl!=l)
        for ns,w in neighbors:
            nc=cost+w
            if nc>=dist.get(ns,1e99):continue
            dist[ns]=nc;parent[ns]=s;heapq.heappush(heap,(nc+heuristic(ns),nc,ns))
    if end is None:return {'ok':False,'reason':'no path','visited':len(seen),'reachable_via':int(sum(via[y,x] for l,y,x in seen))}
    path=[end]
    while path[-1] in parent:path.append(parent[path[-1]])
    path.reverse()
    pts=[starts[path[0]]]+[(x*step,y*step,layers[l]) for l,y,x in path]+[ends[end]]
    # Preserve octilinear routing while removing redundant collinear vertices.
    reduced=[]
    for p in pts:
        if reduced and p==reduced[-1]:continue
        while len(reduced)>1 and p[2]==reduced[-1][2]==reduced[-2][2]:
            a,b=reduced[-2:]
            if abs((b[0]-a[0])*(p[1]-b[1])-(b[1]-a[1])*(p[0]-b[0]))>1e-8:break
            reduced.pop()
        reduced.append(p)
    before=(r.report['added_tracks'],r.report['added_vias'])
    ok=r.commit_xy(reduced,width,net)
    rec={'ok':ok,'visited':len(seen),'path':reduced,'tracks':r.report['added_tracks']-before[0],'vias':r.report['added_vias']-before[1]}
    if not ok:
        bad=[]
        for a,b in zip(reduced,reduced[1:]):
            if a[2]!=b[2]:continue
            g=LineString([a[:2],b[:2]]).buffer(width/2)
            if not r._ok(g,frozenset([a[2]]),net):bad.append([a,b])
        rec['bad_segments']=bad
    return rec


def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('nets',nargs='+');ap.add_argument('--step',type=float,default=.05);ap.add_argument('--width',type=float,default=.127);ap.add_argument('--top-only',action='store_true');ap.add_argument('--report',required=True);args=ap.parse_args()
    report=[]
    for net in args.nets:
        rb.BOARD=Path(args.board);r=Router(rb.load(args.board));r.top_only=args.top_only
        t=time.time();passes=[]
        for attempt in range(20):
            rec=route(r,net,args.width,args.step,args.top_only);passes.append(rec)
            if not rec['ok'] or len(r.groups(net))<2:break
        if r.added:r.write()
        rec={'net':net,'ok':len(r.groups(net))<2,'passes':passes,'seconds':round(time.time()-t,2)}
        report.append(rec);Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
        print({'net':net,'ok':rec['ok'],'groups':len(r.groups(net)),'passes':len(passes),'tracks':r.report['added_tracks'],'vias':r.report['added_vias'],'reason':passes[-1].get('reason'),'seconds':rec['seconds']},flush=True)


if __name__=='__main__':main()
