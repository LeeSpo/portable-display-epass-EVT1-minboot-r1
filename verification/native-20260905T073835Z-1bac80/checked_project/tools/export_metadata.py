#!/usr/bin/env python3
"""Export design-intent pin table/BOM and PCB-derived coordinate PREVIEWS.

Not manufacturing-authorized. CSV formula injection is neutralized in text cells.
Board coordinates are y-down; preview assembly coordinates are bottom-left y-up.
Rotation is the KiCad footprint angle, not a vendor feeder rotation correction.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
from kicad_sexpr import load,children,child,val,values,props
ROOT=Path(__file__).resolve().parents[1]

def safe(value):
    s=str(value)
    return "'"+s if s.startswith(('=','+','-','@')) else s

def pin_csv(root,output):
    c=json.loads((root/'design/pin_contract.json').read_text())['components']
    with Path(output).open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['Reference','Pin','Pin Name','Net'])
        for ref,d in c.items():
            for pn,p in d['pins'].items():w.writerow([ref,pn,p['name'],p['net'] or 'NC'])

def export(root=ROOT,output=None):
    out=Path(output) if output else root/'verification/design_metadata';out.mkdir(parents=True,exist_ok=True)
    contract=json.loads((root/'design/pin_contract.json').read_text())['components'];b=load(root/'portable_display_epass.kicad_pcb')
    fps={str(props(f).get('Reference','')):f for f in children(b,'footprint')}
    origin=list(map(float,values(child(b,'setup'),'aux_axis_origin')))
    if len(origin)!=2:raise ValueError('Explicit PCB placement/drill origin required')
    pin_csv(root,out/'net_pin_report.csv')
    with (out/'placement_PREVIEW_NOT_FOR_ASSEMBLY.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['Reference','X_mm_from_origin','Y_mm_up_from_origin','Side','KiCad_Rotation_deg','Board_X_mm','Board_Y_mm','Status'])
        for ref in contract:
            fp=fps[ref];x,y,*r=map(float,values(fp,'at'));layer=str(val(fp,'layer'));rot=r[0] if r else 0
            w.writerow([ref,round(x-origin[0],5),round(origin[1]-y,5),'Top' if layer=='F.Cu' else 'Bottom',rot%360,x,y,'PREVIEW - feeder rotation and assembly not approved'])
    with (out/'bom_PREVIEW_NOT_FOR_PURCHASE.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['Reference','Value','Footprint','Manufacturer Part','LCSC','Datasheet','DNP','Status'])
        for ref,d in contract.items():
            fp=fps[ref];p=props(fp)
            w.writerow([safe(v) for v in (ref,d['value'],d['footprint'],p.get('MPN',''),p.get('LCSC',''),p.get('Datasheet',''), 'yes' if 'dnp' in values(fp,'attr') else 'no','ENGINEERING PREVIEW')])
    meta={'source_pcb_sha256':hashlib.sha256((root/'portable_display_epass.kicad_pcb').read_bytes()).hexdigest(),'origin_board_xy_mm':origin,'coordinates_from':'actual PCB footprint positions','y_convention':'origin_y minus board_y','rotation_convention':'KiCad CCW; assembly vendor correction not applied','fabrication_released':False,'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.csv')}}
    (out/'metadata_manifest.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args();print(json.dumps(export(output=a.output),indent=2))
