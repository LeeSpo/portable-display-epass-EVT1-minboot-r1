#!/usr/bin/env python3
"""Trim native DRC remnants without splitting a group containing pads."""
import argparse,json
from pathlib import Path
from shapely.geometry import LineString
from finish_power_routes import Router,rb
from plane_connectivity import zones,connected_groups,children,values,val,dumps
ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('drc');ap.add_argument('--report',required=True);args=ap.parse_args()
p=Path(args.board);b=rb.load(p);r=Router(b);zs=zones(b);byid={i.label:i for i in r.items};dr=json.loads(Path(args.drc).read_text());report={'centered':[],'removed':[]}
for v in dr['violations']:
    if v['type']!='track_not_centered_on_via':continue
    its=[byid.get(i['uuid']) for i in v['items']];via=next((i for i in its if i and i.kind=='via'),None);t=next((i for i in its if i and i.kind=='track'),None)
    if not via or not t:continue
    pts=[list(map(float,values(t.node,k))) for k in ['start','end']];j=min(range(2),key=lambda j:sum((pts[j][d]-via.pos[d])**2 for d in range(2)))
    if sum((pts[j][d]-via.pos[d])**2 for d in range(2))>.3**2:continue
    old=pts[j];pts[j]=list(via.pos);g=LineString(pts).buffer(float(val(t.node,'width'))/2)
    if r._ok(g,t.layers,t.net):
        children(t.node,['start','end'][j])[0][1:]=[str(x) for x in via.pos];report['centered'].append({'uuid':t.label,'from':old,'to':list(via.pos)})
r=Router(b);byid={i.label:i for i in r.items};remove=set()
def pad_groups(net,excluding):
    gs=connected_groups([i for i in r.items+zs if i.net==net and i.label not in excluding]);return [set(i.label for i in g if i.kind=='pad') for g in gs if any(i.kind=='pad' for i in g)]
for v in dr['violations']:
    if v['type'] not in ['track_dangling','via_dangling']:continue
    key=v['items'][0]['uuid'];i=byid.get(key)
    if not i:continue
    before=pad_groups(i.net,remove);after=pad_groups(i.net,remove|{key})
    if len(after)<=len(before):remove.add(key);report['removed'].append({'uuid':key,'net':i.net,'reason':v['type']})
b=[n for n in b if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'uuid')) in remove)]
p.write_text(dumps(b)+'\n');Path(args.report).write_text(json.dumps(report,indent=2)+'\n');print({k:len(v) for k,v in report.items()})
