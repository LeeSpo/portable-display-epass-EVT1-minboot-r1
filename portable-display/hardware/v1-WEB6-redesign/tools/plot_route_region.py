#!/usr/bin/env python3
"""Inspect actual copper geometry without changing the PCB."""
import argparse, colorsys
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import box
from finish_power_routes import Router,rb
ap=argparse.ArgumentParser();ap.add_argument('board');ap.add_argument('out');ap.add_argument('--bbox',nargs=4,type=float,required=True);ap.add_argument('--layer',default='F.Cu');args=ap.parse_args()
r=Router(rb.load(args.board));x0,y0,x1,y1=args.bbox;s=180
im=Image.new('RGB',(round((x1-x0)*s)+100,round((y1-y0)*s)+80),'#111822');d=ImageDraw.Draw(im)
font=ImageFont.truetype('/System/Library/Fonts/Monaco.ttf',12)
def xy(p):return (50+(p[0]-x0)*s,40+(p[1]-y0)*s)
for n in range(round(x0*10),round(x1*10)+1):
 x=n/10;d.line([xy((x,y0)),xy((x,y1))],fill='#202833' if n%10 else '#3c4350')
 if n%10==0:d.text(xy((x,y0-.16)),str(x),font=font)
for n in range(round(y0*10),round(y1*10)+1):
 y=n/10;d.line([xy((x0,y)),xy((x1,y))],fill='#202833' if n%10 else '#3c4350')
 if n%10==0:d.text((3,xy((x0,y))[1]),str(y),font=font)
names=sorted(set(i.net for i in r.items));colors={n:tuple(round(c*255) for c in colorsys.hsv_to_rgb(k*.618%1,.53,.88)) for k,n in enumerate(names)}
items=[i for i in r.items if args.layer in i.layers and i.geom.intersects(box(x0,y0,x1,y1))]
for i in sorted(items,key=lambda i:i.kind=='pad'):
 geom=i.geom.intersection(box(x0,y0,x1,y1));polys=[geom] if geom.geom_type=='Polygon' else getattr(geom,'geoms',[])
 for g in polys:
  if g.geom_type=='Polygon':d.polygon([xy(p) for p in g.exterior.coords],fill=colors[i.net])
 if i.kind=='via':
  cx,cy=xy(i.pos);d.ellipse((cx-27,cy-27,cx+27,cy+27),fill='#111822')
for i in items:
 if i.kind=='pad':
  cx,cy=xy(i.pos);label=f'{i.ref}.{i.pin} {i.net}';d.text((cx-14,cy-7),label,fill='white',stroke_width=1,stroke_fill='black',font=font)
 elif i.kind=='track' and i.geom.length>.7:
  a,b=i.pos;cx,cy=xy(((a[0]+b[0])/2,(a[1]+b[1])/2))
  if 0<cx<im.width and 0<cy<im.height:d.text((cx,cy),i.net,fill='white',stroke_width=1,stroke_fill='black',font=font)
im.save(args.out)
