#!/usr/bin/env python3
"""Render actual PCB pad/courtyard geometry; never substitutes for 3D QA."""
import argparse
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT.parent/'v0_legacy/tools'))
from pcb_parser import info
from geometry_audit import board_items
from kicad_sexpr import load
from shapely.geometry import box
from shapely.affinity import rotate,translate

def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('output');ap.add_argument('--copper',action='store_true');a=ap.parse_args()
    b,fs=info(a.board);items=board_items(load(a.board))
    scale=24;ox,oy=85,100;im=Image.new('RGB',(1085,1740),'#f5f7fa');d=ImageDraw.Draw(im)
    font='/System/Library/Fonts/Supplemental/Arial.ttf'
    f=ImageFont.truetype(font,14);small=ImageFont.truetype(font,11);title=ImageFont.truetype(font,25)
    def point(p):return (ox+p[0]*scale,oy+p[1]*scale)
    def poly(g,fill,outline=None):
        if g.geom_type=='MultiPolygon':
            for gg in g.geoms:poly(gg,fill,outline)
        elif g.geom_type=='Polygon':d.polygon([point(p) for p in g.exterior.coords],fill=fill,outline=outline)
    d.text((45,22),'WEB6 | TF-only | Power placement optimization',font=title,fill='#123b49')
    d.text((45,57),'38 x 64 mm | Candidate - not released for fabrication',font=f,fill='#805424')
    d.rectangle([point((0,0)),point((38,64))],fill='#e6eee9',outline='#22685d',width=3)
    for x in range(0,39,2):
        d.text((point((x,0))[0]-8,78),str(x),font=small,fill='#537078')
    for y in range(0,65,2):d.text((50,point((0,y))[1]-6),str(y),font=small,fill='#537078')
    d.rectangle([point((18.1,33.6)),point((22.1,39.085))],fill='#cbe4f2',outline='#709abb')
    d.rectangle([point((8,44.185)),point((24,45.5))],fill='#f6e7c9',outline='#cdaa70')
    if a.copper:
        for i in items:
            if i.kind=='track':poly(i.geom,'#79adb4' if 'B.Cu' in i.layers else '#bd8f89')
    for r,v in fs.items():
        x,y,*aa=v['at'];ang=aa[0] if aa else 0
        if r.startswith('H'):
            d.ellipse([point((x-2.5,y-2.5)),point((x+2.5,y+2.5))],outline='#9aaaaa',width=2)
            d.ellipse([point((x-1.2,y-1.2)),point((x+1.2,y+1.2))],fill='white',outline='#7c9690');continue
        coords=[p for e in v['courtyard'] for p in e]
        if coords:
            g=translate(rotate(box(min(p[0] for p in coords),min(p[1] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords)),-ang,origin=(0,0)),x,y)
            poly(g,'#2d6b73' if r.startswith('U') else '#567766' if r.startswith('L') else '#244756' if r.startswith(('J','SW','Y')) else '#cdd6ce','#879d93')
        for p in items:
            if p.ref==r:poly(p.geom,'#d9b866')
        if r.startswith(('U','L','J','SW','Y')):
            px,py=point((x,y));d.text((px,py),r,anchor='mm',font=f,fill='white',stroke_width=1,stroke_fill='#244756')
        else:
            px,py=point((x,y));d.text((px,py),r,anchor='mm',font=small,fill='#15383a',stroke_width=1,stroke_fill='#e6eee9')
    d.text((85,1665),'Blue: MIPI component keepout   Beige: provisional FPC mating keepout',font=f,fill='#37525b')
    d.text((85,1690),'119 footprints including 4 holes. NAND removed; BOOT0 / BOOT1 retained.',font=f,fill='#37525b')
    im.save(a.output)

if __name__=='__main__':main()
