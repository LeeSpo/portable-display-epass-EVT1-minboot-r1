#!/usr/bin/env python3
"""Include saved native zone fills when identifying redundant routed copper."""
import argparse,json
from pathlib import Path
from shapely.geometry import Polygon
from shapely.strtree import STRtree
from finish_power_routes import Router,rb
from geometry_audit import Item,connected_groups
from kicad_sexpr import children,values,val,dumps

def zones(board):
    out=[]
    for z in children(board,'zone'):
        net=str(val(z,'net_name',val(z,'net','')))
        if not net:continue
        for k,p in enumerate(children(z,'filled_polygon')):
            points=next(iter(children(p,'pts')),None)
            if points is None:continue
            xy=[tuple(map(float,a[1:3])) for a in points[1:] if isinstance(a,list) and a[0]=='xy']
            if len(xy)<3:continue
            g=Polygon(xy).buffer(0)
            for j,poly in enumerate([g] if g.geom_type=='Polygon' else g.geoms):
                out.append(Item('zone',net,frozenset([str(val(p,'layer'))]),poly,z,f'{val(z,"uuid")}/{k}/{j}'))
    return out

def prune(board,nets,layers):
    items=rb.board_items(board)+zones(board);remove=set();report=[]
    for net in nets:
        group=[i for i in items if i.net==net]
        tree=STRtree([i.geom for i in group]);adj={i:set() for i in range(len(group))}
        for i,a in enumerate(group):
            for j in tree.query(a.geom.buffer(1e-6)):
                j=int(j)
                if j<=i:continue
                b=group[j]
                if a.layers&b.layers and a.geom.distance(b.geom)<1e-6:adj[i].add(j);adj[j].add(i)
        candidates=[i for i,a in enumerate(group) if a.kind=='track' and a.layers&set(layers)]
        candidates.sort(key=lambda i:group[i].geom.length,reverse=True)
        removed=[]
        for i in candidates:
            ns=adj[i].copy()
            if len(ns)>1:
                start=next(iter(ns));seen={i,start};todo=[start];need=ns-{start}
                while todo and need:
                    q=todo.pop()
                    for n in adj[q]:
                        if n not in seen:seen.add(n);todo.append(n);need.discard(n)
                if need:continue
            for n in ns:adj[n].discard(i)
            adj[i].clear();remove.add(group[i].label);removed.append(group[i].label)
        report.append({'net':net,'removed':removed})
    return remove,report
