#!/usr/bin/env python3
"""Local cleanup using KiCad's own board model; requires subsequent native DRC."""
import argparse,json
from pathlib import Path
import pcbnew
ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--drc');ap.add_argument('--free-cmd-escape',action='store_true');ap.add_argument('--report',required=True);args=ap.parse_args()
b=pcbnew.LoadBoard(args.board);report={'removed':[],'centered':[],'zone_island_policy':[]}
for z in b.Zones():
    if z.GetNetname()=='GND' and z.GetIslandRemovalMode()!=pcbnew.ISLAND_REMOVAL_MODE_ALWAYS:
        report['zone_island_policy'].append(z.m_Uuid.AsString());z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
byid={t.m_Uuid.AsString():t for t in b.GetTracks()}
if args.free_cmd_escape:
    key='3435af7d-5015-5fe4-bf72-d2e59557e29f'
    if key in byid:
        t=byid[key]
        assert isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()=='GND'
        b.Remove(t);report['removed'].append({'uuid':key,'reason':'Redundant GND stitching via blocks U2 SD_CMD escape'})
if args.drc:
    for v in json.loads(Path(args.drc).read_text())['violations']:
        if v['type']=='track_dangling':
            key=v['items'][0]['uuid'];t=byid.get(key)
            if t is not None and not isinstance(t,pcbnew.PCB_VIA) and pcbnew.ToMM(t.GetLength())<=.10001:
                b.Remove(t);report['removed'].append({'uuid':key,'reason':'0.1 mm dangling stub'})
        elif v['type']=='track_not_centered_on_via':
            objs=[byid.get(i['uuid']) for i in v['items']]
            via=next((t for t in objs if isinstance(t,pcbnew.PCB_VIA)),None)
            tr=next((t for t in objs if t is not None and not isinstance(t,pcbnew.PCB_VIA)),None)
            if via is None or tr is None:continue
            p=via.GetPosition();a=tr.GetStart();c=tr.GetEnd()
            da=(a.x-p.x)**2+(a.y-p.y)**2;dc=(c.x-p.x)**2+(c.y-p.y)**2
            if min(da,dc)>pcbnew.FromMM(.3)**2:continue
            old=a if da<dc else c
            if da<dc:tr.SetStart(p)
            else:tr.SetEnd(p)
            report['centered'].append({'uuid':tr.m_Uuid.AsString(),'from':[pcbnew.ToMM(old.x),pcbnew.ToMM(old.y)],'to':[pcbnew.ToMM(p.x),pcbnew.ToMM(p.y)]})
pcbnew.SaveBoard(args.board,b);Path(args.report).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
