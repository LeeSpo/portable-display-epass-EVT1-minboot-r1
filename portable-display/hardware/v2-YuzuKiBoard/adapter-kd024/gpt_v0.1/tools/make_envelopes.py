#!/usr/bin/env python3
"""Nominal/max body envelopes only. Not vendor STEP and not KiCad screenshots."""
from geometry import *
import cadquery as cq
import svgwrite,cairosvg,math,json
b=load();m=ROOT/'kicad/models';m.mkdir(exist_ok=True)
verified=lambda name:name.startswith(('Hirose_','Molex_','TI_','Coilcraft_'))
ass=cq.Assembly(name='REVIEW_ONLY_NOT_FABRICATION_RELEASED')
x0,y0,x1,y1=b['board']
pcb=cq.Workplane('XY').box(x1-x0,y1-y0,1,centered=(False,False,False)).translate((x0,-y1,-1))
for x,y,r,keep in b['holes']:
 pcb=pcb.cut(cq.Workplane('XY').circle(r).extrude(3).translate((x,-y,-2)))
ass.add(pcb,name='board_1mm',color=cq.Color(.16,.34,.27))
for name,sp in b['footprints'].items():
 if not verified(name):continue
 a,c,z,e=sp['body'];h=sp['height']
 s=cq.Workplane('XY').box(z-a,e-c,h,centered=(False,False,False)).translate((a,-e,0))
 cq.exporters.export(s,str(m/(name+'.step')))
for p in b['parts']:
 if p['dnp'] or p['feature'] or not verified(p['footprint']):continue
 sp=b['footprints'][p['footprint']];a,c,z,e=sp['body'];h=sp['height']
 s=cq.Workplane('XY').box(z-a,e-c,h,centered=(False,False,False)).translate((a,-e,0)).rotate((0,0,0),(0,0,1),p['angle']).translate((p['x'],-p['y'],0))
 ass.add(s,name=p['ref'],color=cq.Color(.24,.25,.27))
ass.export(str(ROOT/'docs/adapter_v0.1_body_envelope.step'))
# Orthographic CAD envelope view. Exact board XY and cited body heights only.
d=svgwrite.Drawing(str(ROOT/'previews/05_body_envelope_NOT_NATIVE_3D.svg'),size=(1600,1200),viewBox='0 0 1600 1200')
d.add(d.rect((0,0),(1600,1200),fill='#f6f8fa'))
d.add(d.text('BODY ENVELOPE REVIEW / NOT A KICAD 3D SCREENSHOT',insert=(50,55),font_size=28,font_family='DejaVu Sans',fill='#173248'))
d.add(d.text('No vendor CAD detail. Passive/header heights and cable/latch motion remain unverified.',insert=(50,88),font_size=20,font_family='DejaVu Sans',fill='#a23e33'))
def pr(x,y,z=0):
 # Far board edge at top, front (J1) at bottom.
 xx=x-71;yy=y-63
 return 800+(xx-yy)*16,610+(xx+yy)*8-z*34

def face(points,fill,stroke='#476358'):
 d.add(d.polygon([pr(*v) for v in points],fill=fill,stroke=stroke,stroke_width=.8))
face([(x0,y0,-1),(x1,y0,-1),(x1,y1,-1),(x0,y1,-1)],'#274737')
face([(x0,y1,-1),(x1,y1,-1),(x1,y1,0),(x0,y1,0)],'#193d2a')
face([(x1,y0,-1),(x1,y1,-1),(x1,y1,0),(x1,y0,0)],'#203e30')
face([(x0,y0,0),(x1,y0,0),(x1,y1,0),(x0,y1,0)],'#367252')
for a in b['pads']:
 if a['kind']=='np_thru_hole':continue
 g=pad_shape(a);pts=[(x,y,.015) for x,y in list(g.exterior.coords)]
 face(pts,'#d5b96b',stroke='#ad9150')
for x,y,r,keep in b['holes']:
 face([(x+r*math.cos(t),y+r*math.sin(t),.02) for t in [k*math.pi/24 for k in range(49)]],'#eef1f4','#213d2b')
for p in sorted(b['parts'],key=lambda p:p['x']+p['y']):
 if p['dnp'] or p['feature'] or not verified(p['footprint']):continue
 sp=b['footprints'][p['footprint']];h=sp['height'];pts=list(body_shape(p,b).exterior.coords)[:4]
 for a,c in zip(pts,pts[1:]+pts[:1]):face([(a[0],a[1],0),(c[0],c[1],0),(c[0],c[1],h),(a[0],a[1],h)],'#41494d','#2d363a')
 face([(x,y,h) for x,y in pts],'#647179' if p['ref'].startswith('J') else '#48535a','#26323a')
 x,y=pr(p['x'],p['y'],h+.04);d.add(d.text(p['ref'],insert=(x,y),text_anchor='middle',font_size=15,font_family='DejaVu Sans',fill='white'))
for j,t in enumerate(['Board: 42 x 38 x 1.0 mm. M2 holes: 2.2 mm NPTH; copper/body keepout radius 2.6 mm.', 'Models: J1/J2, U1-U4 and L1/L2 body envelopes. Excludes terminals, latch travel and FFC bend.', 'Flat gold pads are NOT assembled parts; unknown-height passives and manual headers omitted.', 'REVIEW HOLD: FFC mapping, panel bias limits, native ERC/DRC, impedance and SMT orientation are NOT signed off.']):
 d.add(d.text(t,insert=(50,1050+j*30),font_size=19,font_family='DejaVu Sans',fill='#a23e33' if j==3 else '#425967'))
d.save();cairosvg.svg2png(url=str(ROOT/'previews/05_body_envelope_NOT_NATIVE_3D.svg'),write_to=str(ROOT/'previews/05_body_envelope_NOT_NATIVE_3D.png'))
print('Envelope STEP models and labeled isometric review produced.')
