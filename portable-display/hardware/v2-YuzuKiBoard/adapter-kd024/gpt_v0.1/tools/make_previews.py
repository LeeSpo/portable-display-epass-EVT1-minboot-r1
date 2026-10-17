#!/usr/bin/env python3
from geometry import *
from native_io import read_pcb
import json,math,pathlib,fitz,svgwrite,cairosvg
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
b=load();views=json.loads((ROOT/'reports/schematic_views.json').read_text());W,H=420*mm,297*mm
cv=canvas.Canvas(str(ROOT/'docs/adapter_v0.1_schematic.pdf'),pagesize=(W,H));cv.setTitle('Lizard to KD024 - Schematic review, not native KiCad export')
def text(x,y,t,size=1,align='left',color='#16364d',bold=False):
 cv.setFillColor(HexColor(color));cv.setFont('Helvetica-Bold' if bold else 'Helvetica',size*mm*1.4)
 fun={'left':cv.drawString,'right':cv.drawRightString,'center':cv.drawCentredString}[align];fun(x*mm,(297-y)*mm,t)
def line(a,c,width=.15,color='#375f52'):
 cv.setStrokeColor(HexColor(color));cv.setLineWidth(width*mm);cv.line(a[0]*mm,(297-a[1])*mm,c[0]*mm,(297-c[1])*mm)
for page,sec in enumerate(['root','bias','logic'],1):
 v=views[sec]
 cv.setStrokeColor(HexColor('#b8c5ce'));cv.setLineWidth(.2*mm);cv.rect(10*mm,10*mm,400*mm,277*mm)
 for x,y,size,t in v['texts']:text(x,y,t,size,'left','#a03b30' if 'HOLD' in t else '#173248')
 for it in v['items']:
  p=it['part'];x,y=p['sch_xy'];sp=it['geom'];w,h=sp['w'],sp['h'];typ=p['symbol']
  text(x,y-h-6.35,p['ref'],1.45,'center',bold=True)
  text(x,y-h-3.81,p['value'],1.00,'center','#505d67')
  cv.setStrokeColor(HexColor('#1d3748'));cv.setLineWidth(.2*mm)
  if typ=='C':
   line((x-.635,y-1.524),(x-.635,y+1.524),.25,'#1d3748');line((x+.635,y-1.524),(x+.635,y+1.524),.25,'#1d3748')
  elif typ=='R':cv.rect((x-2.54)*mm,(297-y-.9)*mm,5.08*mm,1.8*mm)
  elif typ=='L':
   pts=[(x-2.54+i*5.08/32,y-.75*abs(math.sin(i*math.pi/8))) for i in range(33)]
   for a,c in zip(pts,pts[1:]):line(a,c,.25,'#1d3748')
  elif typ in ['TP','Mechanical']:cv.circle(x*mm,(297-y)*mm,1*mm)
  else:
   cv.setFillColor(HexColor('#f4f7f9'));cv.rect((x-w)*mm,(297-y-h)*mm,2*w*mm,2*h*mm,fill=1)
  for pin in it['pins']:
   px,py=pin['x'],pin['y'];right=px>x;bodyx=px+(-pin['length'] if right else pin['length']);
   line((px,py),(bodyx,py),.18,'#1d3748')
   if typ not in ['C','R','L','TP','Mechanical']:
    text(bodyx-.8 if right else bodyx+.8,py+.3,pin['name'],.92,'right' if right else 'left')
   text((px+bodyx)/2,py-.45,pin['num'],.78,'center','#6d5b58')
   if pin['net']:
    ex=pin['label_x'];line((px,py),(ex,py),.18)
    text(ex+.6 if right else ex-.6,py+.32,pin['net'],.94,'left' if right else 'right','#176245')
   else:
    line((px-.5,py-.5),(px+.5,py+.5),.15,'#406ca5');line((px-.5,py+.5),(px+.5,py-.5),.15,'#406ca5')
  if p['dnp']:
   text(x,y+h+3,'DNP / NOT ASSEMBLED',1.0,'center','#a03b30')
 if sec=='root':
  for j,ss in enumerate(['bias','logic']):
   x,y=335,64+j*55;cv.setStrokeColor(HexColor('#526b7d'));cv.setLineWidth(.3*mm);cv.rect(x*mm,(297-y-23)*mm,63*mm,23*mm)
   text(x+4,y+9,ss.upper()+' SUBSHEET',1.7,bold=True);text(x+4,y+16,{'bias':'power_bias.kicad_sch','logic':'logic_control.kicad_sch'}[ss],1.)
 for net,x,y in v['flags']:
  cv.setStrokeColor(HexColor('#526b7d'));cv.circle(x*mm,(297-y)*mm,1*mm)
  line((x-2.54,y),(x,y),.15);text(x,y-2,'PWR_FLAG',.8,'center');text(x-3,y+.3,net,.85,'right','#176245')
 text(12,294,'Generated from the same pin/net model as the editable schematic; NOT kicad-cli output. Native ERC/DRC not run.',1.05,'left','#6a3941')
 text(408,294,f'{page} / 3',1.05,'right')
 cv.showPage()
cv.save()
# Render the actual PDF pages for inspection, rather than separate artwork.
doc=fitz.open(ROOT/'docs/adapter_v0.1_schematic.pdf')
for i,page in enumerate(doc):page.get_pixmap(matrix=fitz.Matrix(2.0,2.0),alpha=False).save(ROOT/'previews'/f'schematic_page_{i+1}.png')
# Pin-one / rotation overview: exact pad geometry, not a native 3D screenshot.
d=svgwrite.Drawing(str(ROOT/'previews/03_pin1_rotation_review.svg'),size=(1500,840),viewBox='0 0 1500 840');d.add(d.rect((0,0),(1500,840),fill='#f7f9fc'))
d.add(d.text('PIN 1 / TOP-SIDE ROTATION REVIEW',insert=(45,45),font_size=26,font_family='DejaVu Sans',fill='#173248'))
d.add(d.text('Native PCB coordinates. Not a KiCad 3D or JLC assembly screenshot. Physical orientation signoff remains open.',insert=(45,73),font_size=15,font_family='DejaVu Sans',fill='#a34136'))
for i,ref in enumerate(['J1','J2','U1','U2']):
 p=next(p for p in b['parts'] if p['ref']==ref);sp=b['footprints'][p['footprint']];cx,cy=(390,250) if i==0 else (1110,250) if i==1 else (390,625) if i==2 else (1110,625);sc=35 if i<2 else 60
 # Use actual transformed geometry centered at each component's placement origin.
 def xy(v):return (cx+(v[0]-p['x'])*sc,cy+(v[1]-p['y'])*sc)
 body=body_shape(p,b);d.add(d.polygon([xy(v) for v in body.exterior.coords],fill='#e1e7ed',stroke='#425c70',stroke_width=1.5))
 for a in [a for a in b['pads'] if a['ref']==ref]:
  g=pad_shape(a);d.add(d.polygon([xy(v) for v in g.exterior.coords],fill='#bd9960',stroke='#7b673f',stroke_width=.7))
  px,py=xy((a['x'],a['y']));d.add(d.text(a['num'],insert=(px,py+3),text_anchor='middle',font_size=9 if i<2 else 12,font_family='DejaVu Sans',fill='#132938'))
  if a['num']=='1':
   d.add(d.circle((px,py),11,fill='none',stroke='#be3f36',stroke_width=2));d.add(d.text('PIN 1',insert=(px+16,py-16),font_size=14,font_family='DejaVu Sans',fill='#be3f36'))
 d.add(d.text(f'{ref}  |  Rotation {p["angle"]} deg  |  TOP',insert=(cx,cy-135 if i<2 else cy-137),text_anchor='middle',font_size=20,font_family='DejaVu Sans',fill='#173248'))
 d.add(d.text(f'PCB origin X={p["x"]:.4f}  Y={p["y"]:.4f} mm',insert=(cx,cy+123 if i<2 else cy+133),text_anchor='middle',font_size=14,font_family='DejaVu Sans',fill='#526777'))
d.save();cairosvg.svg2png(url=str(ROOT/'previews/03_pin1_rotation_review.svg'),write_to=str(ROOT/'previews/03_pin1_rotation_review.png'))
# DSI hold: endpoint coordinates and honest N/A length instead of fictitious tuning.
d=svgwrite.Drawing(str(ROOT/'previews/04_DSI_HOLD.svg'),size=(1400,880),viewBox='0 0 1400 880');d.add(d.rect((0,0),(1400,880),fill='#f7f9fc'))
d.add(d.text('DSI ROUTING: BLOCKED BY REQUIRED IMPEDANCE EVIDENCE',insert=(50,55),font_size=27,font_family='DejaVu Sans',fill='#173248'))
lines=['Target: JLC04101H-3313 / 1.0 mm / Top to In1 GND / 100 ohm differential.', 'Official dielectric thickness, finished copper, Dk and calculator result: NOT VERIFIED.', 'Width W: N/A     Edge gap S: N/A     End-to-end route lengths: N/A.', 'There are NO DSI copper tracks or vias in this PCB. These lines only show required connectivity.']
for j,s in enumerate(lines):d.add(d.text(s,insert=(50,100+29*j),font_size=17,font_family='DejaVu Sans',fill='#a34136' if j>1 else '#425c70'))
for i,net in enumerate(['DSI_D0_P','DSI_D0_N','DSI_CK_P','DSI_CK_N']):
 ps=[a for a in b['pads'] if a['net']==net];a=next(a for a in ps if a['ref']=='J1');c=next(a for a in ps if a['ref']=='J2');y=300+i*104
 d.add(d.text(net,insert=(50,y),font_size=21,font_family='DejaVu Sans',fill='#173248'))
 d.add(d.text(f'J1-{a["num"]}: ({a["x"]:.4f}, {a["y"]:.4f})',insert=(250,y),font_size=18,font_family='DejaVu Sans',fill='#425c70'))
 d.add(d.line((655,y-7),(895,y-7),stroke='#b09a6c',stroke_width=2,stroke_dasharray='8 7'))
 d.add(d.text(f'J2-{c["num"]}: ({c["x"]:.4f}, {c["y"]:.4f})',insert=(930,y),font_size=18,font_family='DejaVu Sans',fill='#425c70'))
 d.add(d.text('UNROUTED - no impedance or length compliance claim',insert=(250,y+28),font_size=15,font_family='DejaVu Sans',fill='#a34136'))
for j,s in enumerate(['Required after routing: P/N skew <= 0.15 mm; D0/CK pair-to-pair difference <= 1.00 mm.', 'All copper on Top; no vias / probe stubs; continuous In1 return; >= 3 mm from SWP/SWN and inductors.', 'This review view does NOT satisfy the requested annotated routed-trace screenshot.']):
 d.add(d.text(s,insert=(50,766+j*27),font_size=16,font_family='DejaVu Sans',fill='#425c70'))
d.save();cairosvg.svg2png(url=str(ROOT/'previews/04_DSI_HOLD.svg'),write_to=str(ROOT/'previews/04_DSI_HOLD.png'))
print('Schematic PDF and pin/DSI review images generated.')
