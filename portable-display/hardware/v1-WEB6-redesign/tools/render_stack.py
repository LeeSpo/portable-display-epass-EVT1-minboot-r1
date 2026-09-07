#!/usr/bin/env python3
"""Render four copper layers from saved copper, including filled zones."""
import argparse,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from finish_power_routes import Router,rb
from kicad_sexpr import children,values,val

COLORS={'GND':'#214f42','CORE_0V93':'#ed8766','DRAM_1V5':'#e5c55c','1V8':'#62b5e5','3V3':'#ad8ae5','VSYS':'#66c8a0'}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('--output',required=True);o=ap.parse_args()
    b=rb.load(o.board);r=Router(b);scale=12;pw=496
    im=Image.new('RGB',(pw*4,930),'#101b24');d=ImageDraw.Draw(im)
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20)
    small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',16)
    for k,l in enumerate(['F.Cu','In1.Cu','In2.Cu','B.Cu']):
        def xy(p):return (k*pw+20+p[0]*scale,65+p[1]*scale)
        d.text((k*pw+20,20),l,fill='white',font=font)
        for z in children(b,'zone'):
            net=str(val(z,'net',''));color=COLORS.get(net,'#887566')
            for poly in children(z,'filled_polygon'):
                if str(val(poly,'layer'))!=l:continue
                pts=[xy(tuple(map(float,p[1:3]))) for p in children(children(poly,'pts')[0],'xy')]
                if len(pts)>2:d.polygon(pts,fill=color)
        def geom(g,color):
            if g.geom_type=='Polygon':
                d.polygon([xy(p) for p in g.exterior.coords],fill=color)
                for h in g.interiors:d.polygon([xy(p) for p in h.coords],fill='#101b24')
        for i in r.items:
            if l in i.layers:geom(i.geom,COLORS.get(i.net,'#bfc8ce'))
            if i.hole is not None:geom(i.hole,'#101b24')
        d.rectangle([xy((0,0)),xy((38,64))],outline='#eeeeee',width=2)
    for j,(n,c) in enumerate(COLORS.items()):
        x=25+j*230;d.rectangle((x,855,x+18,873),fill=c);d.text((x+25,853),n,fill='white',font=small)
    d.text((25,896),'Engineering candidate - not fabrication release. Copper shown from saved board.',fill='#e7b36b',font=small)
    im.save(o.output)

if __name__=='__main__':main()
