#!/usr/bin/env python3
"""Prune only native-DRC dangling copper; keep unconnected-net errors visible."""
import argparse,json,subprocess
from pathlib import Path
from finish_power_routes import rb
from kicad_sexpr import dumps,val,children

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--report',required=True);ap.add_argument('--drc',required=True);o=ap.parse_args()
    p=Path(o.board);log=[]
    for turn in range(16):
        subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--refill-zones','--format','json','-o',o.drc,str(p)],check=True,stdout=subprocess.DEVNULL)
        j=json.loads(Path(o.drc).read_text());ids={i['uuid'] for v in j['violations'] if v['type'] in ['track_dangling','via_dangling'] for i in v['items']}
        b=rb.load(p);remove=[n for n in b if isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'uuid')) in ids and not children(n,'locked')]
        if not remove:break
        log.extend({'uuid':str(val(n,'uuid')),'net':str(val(n,'net')),'type':n[0]} for n in remove)
        b=[n for n in b if n not in remove];p.write_text(dumps(b)+'\n')
    Path(o.report).write_text(json.dumps({'removed':log,'rounds':turn+1},indent=2));print('Removed',len(log),'items')

if __name__=='__main__':main()
