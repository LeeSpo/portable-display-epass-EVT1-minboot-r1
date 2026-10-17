#!/usr/bin/env python3
from geometry import *
import svgwrite, cairosvg, math
b=load();scale=24;W=1200;H=1140
colors={'F.Cu':'#d45244','In1.Cu':'#94823a','In2.Cu':'#7798d2','B.Cu':'#407571'}
def render(name,layers,annot=True):
 d=svgwrite.Drawing(str(ROOT/'previews'/name),size=(W,H),viewBox=f'0 0 {W} {H}')
 d.add(d.rect((0,0),(W,H),fill='#f8fafc'))
 d.add(d.text('LIZARD  /  KD024    v0.1 review',insert=(70,43),font_size=24,font_family='DejaVu Sans',fill='#182c42'))
 d.add(d.text('ENGINEERING HOLD  |  DSI copper intentionally not routed  |  not KiCad DRC or 3D evidence',insert=(70,72),font_size=13,font_family='DejaVu Sans',fill='#a33c2d'))
 ox,oy=70,100
 def xy(x,y):return (ox+(x-50)*scale,oy+(y-44)*scale)
 def shape(g,fill,stroke='none',sw=.5,opacity=1):
  for p in polys(g):
   d.add(d.polygon([xy(*v) for v in p.exterior.coords],fill=fill,stroke=stroke,stroke_width=sw,opacity=opacity))
 shape(box(*b['board']),'#174139','#40575b',1)
 for x,y,dr,kr in b['holes']:
  d.add(d.circle(xy(x,y),kr*scale,fill='none',stroke='#c6cfad',stroke_width=.8,stroke_dasharray='5 4'))
 for layer in layers:
  for t in b['tracks']:
   if t['layer']==layer:d.add(d.line(xy(*t['a']),xy(*t['b']),stroke=colors[layer],stroke_width=t['width']*scale,stroke_linecap='round',opacity=.85 if layer=='F.Cu' else .7))
 for v in b['vias']:
  d.add(d.circle(xy(v['x'],v['y']),v['size']/2*scale,fill='#b9bd91',stroke='#162c34',stroke_width=.5))
  d.add(d.circle(xy(v['x'],v['y']),v['drill']/2*scale,fill='#142c37'))
 for p in b['pads']:
  g=pad_shape(p)
  if p['kind']=='np_thru_hole':shape(g,'#f8fafc','#24364c',1);continue
  shape(g,'#d4bd7c','#68582c',.5)
  if p.get('drill'):d.add(d.circle(xy(p['x'],p['y']),p['drill']/2*scale,fill='#142c37'))
 for p in b['parts']:
  if p['feature']:continue
  shape(body_shape(p,b),'none','#f3eddf',.7)
  tx,ty=xy(p['x'],p['y']);d.add(d.text(p['ref'],insert=(tx,ty-3),text_anchor='middle',font_size=9,font_family='DejaVu Sans',fill='white'))
  if p['ref'] in ['J1','J2','U1','U2','U3','U4']:
   pp=next(z for z in b['pads'] if z['ref']==p['ref'] and z['num']=='1');tx,ty=xy(pp['x'],pp['y']);d.add(d.text('1',insert=(tx+7,ty-6),font_size=10,font_weight='bold',font_family='DejaVu Sans',fill='white'))
 if annot:
  for net in b['dsi_nets']:
   pp=[p for p in b['pads'] if p['net']==net]
   d.add(d.line(xy(pp[0]['x'],pp[0]['y']),xy(pp[1]['x'],pp[1]['y']),stroke='#f9eabc',stroke_width=1,stroke_dasharray='6 6'))
  # Size and known mechanical row spacing, outside the copper area.
  d.add(d.text('42.000 mm',insert=(ox+21*scale,oy+38*scale+27),text_anchor='middle',font_size=13,font_family='DejaVu Sans',fill='#253e53'))
  d.add(d.text('38.000 mm',insert=(25,oy+19*scale),transform=f'rotate(-90 25 {oy+19*scale})',text_anchor='middle',font_size=13,font_family='DejaVu Sans',fill='#253e53'))
  d.add(d.text('H1 / H2 centres: 19.913 mm    |    1.0 mm drill / 1.7 mm land',insert=(70,1050),font_size=13,font_family='DejaVu Sans',fill='#253e53'))
  d.add(d.text('Dashed lines = unconnected net indicators, NOT physical routes.  Copper line colours are layer keys.',insert=(70,1074),font_size=12,font_family='DejaVu Sans',fill='#526372'))
 d.save();cairosvg.svg2png(url=str(ROOT/'previews'/name),write_to=str(ROOT/'previews'/name.replace('.svg','.png')))
render('01_top_layout_review.svg',['F.Cu'])
render('02_multilayer_layout_review.svg',['B.Cu','In2.Cu','F.Cu'])
