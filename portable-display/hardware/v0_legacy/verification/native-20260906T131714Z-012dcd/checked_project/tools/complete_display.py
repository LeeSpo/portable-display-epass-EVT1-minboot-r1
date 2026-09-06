#!/usr/bin/env python3
"""Route reviewed display/repair nets into a candidate, never regenerate a PCB.

Uses the existing clearance-aware F/B router. Ground stitches terminate on the
In1 ground plane; all results require native refill and DRC. MIPI and USB pairs
are explicitly excluded from this single-net router. No SI/fabrication approval.
"""
import argparse,json,math
from pathlib import Path
from complete_minboot import Closure
from kicad_sexpr import load,dump,children,props,setval,Q
from geometry_audit import board_items,issues
import complete_minboot as closure
import generate_evt1 as gen

class DisplayClosure(Closure):
    def close(self,net):
        if net.startswith(("DSI_", "USB_")):
            raise ValueError("High-speed pairs must not be routed as single nets")
        return super().close(net)


def ground_stitches(r, pad_filter=None):
    refs={'J4','U10','L5','L6','C42','C43','C44','C45','C46','C47','C48','C49','C50','C51'}
    result={}
    for pad in list(r.items):
        if pad.kind!='pad' or pad.ref not in refs or pad.net!='GND':continue
        if pad_filter is not None and pad.label not in pad_filter:continue
        x,y=pad.pos
        options=[]
        if pad.ref=='U10' and pad.pin=='13':options=[(x,y),(x,y-.6),(x,y+.6)]
        elif pad.ref=='J4':
            direction=1 if pad.pin.startswith('MP') or int(pad.pin)%2 else -1
            options=[(x+dx,y+direction*dy) for dy in [.7,.9,1.1] for dx in [0,-.15,.15,-.3,.3]]
        else:
            for rad in [.65,.85,1.05,1.3]:
                options.extend((x+rad*math.cos(a*math.pi/4),y+rad*math.sin(a*math.pi/4)) for a in range(8))
        for vx,vy in options:
            if any(i.kind=='via' and i.net=='GND' and math.dist(i.pos,(vx,vy))<.01 for i in r.items):continue
            pieces=[('seg',(x,y,vx,vy,.12 if pad.ref=='J4' else .2,'F.Cu','GND','display-gnd-'+pad.label)),('via',(vx,vy,'GND','display-gnd-'+pad.label))]
            if r.commit(pieces):result[pad.label]=(vx,vy);break
        else:result[pad.label]=None
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--filled',type=Path,required=True)
    p.add_argument('--nets',required=True);p.add_argument('--stitch',action='store_true');a=p.parse_args()
    nets=a.nets.split(',')
    if any(n.startswith(('DSI_','USB_')) for n in nets):p.error('Route high-speed differential pairs together, not as single nets')
    b=load(a.input);r=DisplayClosure(b,load(a.filled))
    # Current schematic fields use dev.note, not the library fallback MPN.
    devs={d.ref:d for d in gen.devices()}
    for f in children(b,'footprint'):
        ref=props(f).get('Reference')
        if ref in devs:
            for prop in children(f,'property'):
                if prop[1]=='Description':prop[2]=Q(devs[ref].note)
    result={}
    if a.stitch:result['ground_stitches']=ground_stitches(r);dump(b,a.output)
    # Output/feed routes use wider copper; CT and GPIO retain small escape widths.
    original=closure.width_for
    closure.width_for=lambda n:.25 if n in {'ELVDD','ELVSS','EL_SWP','EL_SWN','LCD_3V3','LCD_1V8','SOC_LDO_1V8'} else original(n)
    for n in nets:
        print('START',n,flush=True);result[n]=r.close(n);print('RESULT',n,result[n],flush=True)
        r._strip_zone_fills();dump(b,a.output)
    result['geometry_issues']=issues(board_items(b));result['tracks_added']=r.report['added_tracks'];result['vias_added']=r.report['added_vias']
    a.output.with_suffix('.routing.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
