#!/usr/bin/env python3
"""Close power links against native filled copper, and remove floating remnants."""
import argparse,json
from pathlib import Path
from plane_connectivity import zones,connected_groups,rb,dumps,val
from finish_power_routes import Router
from route_remaining import route
ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--nets',nargs='*',default=['CORE_0V93','3V3','1V8','DRAM_1V5','VSYS','SOC_LDO_1V8']);ap.add_argument('--report',required=True);args=ap.parse_args()
p=Path(args.board);rb.BOARD=p;b=rb.load(p);zs=zones(b);items=rb.board_items(b)
allgroups=connected_groups(items+zs,net_aware=True);remove=set()
for g in allgroups:
    if any(i.kind=='pad' for i in g):continue
    remove.update(i.label for i in g if i.kind in ['track','via'])
b=[n for n in b if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'uuid')) in remove)]
p.write_text(dumps(b)+'\n');report={'floating_removed':sorted(remove),'nets':[]};r=Router(b)
for net in args.nets:
    recs=[]
    for attempt in range(20):
        gs=connected_groups([i for i in r.items+zs if i.net==net]);gs=[g for g in gs if any(i.kind=='pad' for i in g)]
        if len(gs)<2:break
        gs.sort(key=len)
        progress=False
        for source in gs[:-1]:
            target=[i for g in gs if g is not source for i in g]
            r.groups=lambda n,source=source,target=target:[source,target]
            for width in [.6,.4,.25]:
                rec=route(r,net,width,.05);rec['width']=width
                if rec['ok']:
                    recs.append(rec);progress=True;break
            if progress:break
        if not progress:break
    gs=connected_groups([i for i in r.items+zs if i.net==net]);gs=[g for g in gs if any(i.kind=='pad' for i in g)]
    result={'net':net,'connected':len(gs)<2,'groups':[[i.label for i in g if i.kind=='pad'] for g in gs],'routes':recs}
    report['nets'].append(result);print(net,'pad groups',len(gs),'routes',len(recs),flush=True)
r.write();Path(args.report).write_text(json.dumps(report,indent=2)+'\n')
