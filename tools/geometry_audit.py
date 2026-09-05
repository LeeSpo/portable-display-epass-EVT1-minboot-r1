from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import math,collections,json
from shapely.geometry import Point,LineString,box
from shapely import affinity
from shapely.strtree import STRtree
from kicad_sexpr import *
LAYERS=frozenset(('F.Cu','In1.Cu','In2.Cu','B.Cu'))
@dataclass
class Item:
    kind:str
    net:str
    layers:frozenset
    geom:object
    node:list
    label:str
    hole:object=None
    ref:str=''
    pin:str=''
    pos:tuple=()

def xy(vals):return tuple(map(float,vals[:2]))
def rotation(x,y,deg):
    a=math.radians(deg)
    return x*math.cos(a)+y*math.sin(a),-x*math.sin(a)+y*math.cos(a)

def board_items(board):
    nets={str(n[1]):str(n[2]) for n in children(board,'net')}
    def netname(node):
        n=values(node,'net')
        return str(n[-1]) if len(n)>1 else nets.get(str(n[0]),str(n[0])) if n else ''
    items=[]
    for f in children(board,'footprint'):
        ref=str(props(f).get('Reference',''))
        x,y,*angles=map(float,values(f,'at'));fa=angles[0] if angles else 0
        for pad in children(f,'pad'):
            px,py,*pa=map(float,values(pad,'at'));px,py=rotation(px,py,fa);px+=x;py+=y
            sx,sy=xy(values(pad,'size'));angle=pa[0] if pa else 0
            if pad[3]=='circle':g=Point(0,0).buffer(sx/2,quad_segs=24)
            elif pad[3]=='oval':
                g=LineString(((-(sx-sy)/2,0),((sx-sy)/2,0))).buffer(sy/2,quad_segs=24) if sx>sy else LineString(((0,-(sy-sx)/2),(0,(sy-sx)/2))).buffer(sx/2,quad_segs=24)
            elif pad[3]=='roundrect':
                r=min(sx,sy)*float(val(pad,'roundrect_rratio',0.2))
                g=box(-sx/2+r,-sy/2+r,sx/2-r,sy/2-r).buffer(r,quad_segs=12)
            else:g=box(-sx/2,-sy/2,sx/2,sy/2)
            g=affinity.translate(affinity.rotate(g,-angle,origin=(0,0)),px,py)
            ls=values(pad,'layers');layers=LAYERS if '*.Cu' in ls else frozenset(l for l in ls if str(l).endswith('.Cu'))
            drill=values(pad,'drill');hole=Point(px,py).buffer(float(drill[-1])/2,quad_segs=24) if drill else None
            if pad[2]=='np_thru_hole':layers=frozenset()
            items.append(Item('pad',netname(pad),layers,g,pad,ref+'.'+str(pad[1]),hole,ref,str(pad[1]),(px,py)))
    for t in children(board,'segment'):
        p1,p2=xy(values(t,'start')),xy(values(t,'end'));w=float(val(t,'width'))
        items.append(Item('track',netname(t),frozenset((str(val(t,'layer')),)),LineString((p1,p2)).buffer(w/2,quad_segs=16),t,str(val(t,'uuid','track')),pos=(p1,p2)))
    for v in children(board,'via'):
        p=xy(values(v,'at'));r=float(val(v,'size'))/2;d=float(val(v,'drill'))/2
        items.append(Item('via',netname(v),LAYERS,Point(p).buffer(r,quad_segs=24),v,str(val(v,'uuid','via')),Point(p).buffer(d,quad_segs=24),pos=p))
    return items

class DSU:
    def __init__(self,n):self.p=list(range(n))
    def find(self,x):
        while self.p[x]!=x:self.p[x]=self.p[self.p[x]];x=self.p[x]
        return x
    def union(self,a,b):self.p[self.find(a)]=self.find(b)

def connected_groups(items,net_aware=False):
    tree=STRtree([i.geom for i in items]);d=DSU(len(items))
    for i,a in enumerate(items):
        for j in tree.query(a.geom.buffer(1e-6)):
            j=int(j)
            if j<=i:continue
            b=items[j]
            if a.layers&b.layers and (not net_aware or a.net==b.net) and a.geom.distance(b.geom)<1e-6:d.union(i,j)
    groups=collections.defaultdict(list)
    for n,a in enumerate(items):groups[d.find(n)].append(a)
    return list(groups.values())

def issues(items,clearance=.09,hole_clearance=.25,hole_to_hole=.25):
    tree=STRtree([i.geom for i in items]);results=[]
    for i,a in enumerate(items):
        for j in tree.query(a.geom.buffer(max(clearance,hole_clearance)+.02)):
            j=int(j)
            if j<=i:continue
            b=items[j]
            same=bool(a.net) and a.net==b.net
            # Copper spacing applies only on common copper layers.
            if not same and a.layers&b.layers:
                gap=a.geom.distance(b.geom)
                if gap<clearance-1e-5:results.append({'type':'copper_clearance','gap':round(gap,6),'a':a.label,'an':a.net,'b':b.label,'bn':b.net})
            if a.hole is not None and b.hole is not None:
                gap=a.hole.distance(b.hole)
                if gap<hole_to_hole-1e-5:results.append({'type':'hole_to_hole','gap':round(gap,6),'a':a.label,'an':a.net,'b':b.label,'bn':b.net})
            if not same:
                gaps=[]
                if a.hole is not None and b.layers:gaps.append(a.hole.distance(b.geom))
                if b.hole is not None and a.layers:gaps.append(b.hole.distance(a.geom))
                if gaps and min(gaps)<hole_clearance-1e-5:results.append({'type':'hole_to_copper','gap':round(min(gaps),6),'a':a.label,'an':a.net,'b':b.label,'bn':b.net})
    return results

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser();a.add_argument('board');a.add_argument('--out');opt=a.parse_args()
    b=load(opt.board);it=board_items(b);gr=connected_groups(it)
    conflicts=[];relabels=[];u2=[]
    for g in gr:
        pads=[x for x in g if x.kind=='pad' and x.net]
        nets={x.net for x in pads};copper=[x for x in g if x.kind!='pad']
        if len(nets)>1 and copper:conflicts.append(([p.label+':'+p.net for p in pads],len(copper)))
        if len(nets)==1:
            n=next(iter(nets));wrong=[x for x in copper if x.net!=n]
            if wrong:relabels.append({'pads':[p.label for p in pads],'correct':n,'wrong':[(x.kind,x.net,x.label) for x in wrong]})
        if any(p.ref=='U2' and p.pin!='89' for p in pads):u2.append({'pads':[p.label for p in pads],'copper':len(copper)})
    report={'objects':dict(collections.Counter(x.kind for x in it)),'conflicting_components':conflicts,'relabels':relabels,'u2_components':u2,'issues':issues(it)}
    print('objects',report['objects'],'conflicts',conflicts,'relabels',relabels)
    print('u2 foreign pads',[g for g in u2 if any(not p.startswith('U2.') for p in g['pads'])])
    print('issues',dict(collections.Counter(x['type'] for x in report['issues'])))
    print('sample',report['issues'][:12])
    if opt.out:Path(opt.out).write_text(json.dumps(report,indent=2))
