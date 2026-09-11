#!/usr/bin/env python3
"""Route critical nets on F.Cu, recording copper displaced for later repair."""
import argparse,json
from pathlib import Path
from finish_power_routes import Router,rb
from kicad_sexpr import dumps,val

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--report',required=True);o=ap.parse_args()
    rb.BOARD=Path(o.board);records=[];protected=set(rb.LX)
    for net in ['XIN','XOUT','DSI_CKN','DSI_CKP','DSI_D0N','DSI_D0P','USB_DP','USB_DM','SD_CLK']:
        board=rb.load(o.board);original=Router(board)
        fixed=[n for n in board if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'net')) not in protected|{net})]
        r=Router(fixed);r.top_only=True
        if net=='XIN':
            r.commit_xy([(22.75,26.425,'F.Cu'),(23.4,26.425,'F.Cu'),(23.4,25.825,'F.Cu'),(25.7,25.825,'F.Cu'),(25.7,25.9,'F.Cu')],.127,net)
        ok=r.complete(net,.127)
        added=[i for i in r.items if i.net==net and i.kind=='track' and i.label not in {j.label for j in original.items}]
        remove=set()
        for i in original.items:
            if i.kind not in ['track','via'] or i.net==net:continue
            if any((i.layers&j.layers and i.geom.distance(j.geom)<.127-1e-6) or (i.hole is not None and i.hole.distance(j.geom)<.25-1e-6) for j in added):remove.add(i.label)
        assert not any(i.label in remove and i.net in protected for i in original.items)
        result=[n for n in board if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'uuid')) in remove)]
        Path(o.board).write_text(dumps(result)+'\n');r.write()
        records.append({'net':net,'connected':ok,'removed':[{'uuid':i.label,'net':i.net} for i in original.items if i.label in remove]})
        print(net,ok,'removed',len(remove),flush=True);protected.add(net)
    Path(o.report).write_text(json.dumps(records,indent=2))

if __name__=='__main__':main()
