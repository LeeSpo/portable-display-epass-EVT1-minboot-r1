#!/usr/bin/env python3
"""Render actual PCB geometry to monochrome SVG; zones intentionally omitted.
Not a native KiCad rendering and not a fabrication plot.
"""
from pathlib import Path
import html
from kicad_sexpr import load,children,props,values
from geometry_audit import board_items
ROOT=Path(__file__).resolve().parents[1]

def render(path,window,width):
    b=load(ROOT/'portable_display_epass.kicad_pcb');items=board_items(b)
    x,y,w,h=window
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{width*h/w:.0f}" viewBox="{x} {y} {w} {h}">', '<title>Actual PCB geometry preview - zones excluded - not for fabrication</title>',f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="white"/>','<rect x="0" y="0" width="58" height="110" fill="none" stroke="black" stroke-width=".12"/>']
    for i in items:
        if 'F.Cu' not in i.layers:continue
        points=' '.join(f'{a:.5f},{b:.5f}' for a,b in i.geom.exterior.coords)
        out.append(f'<polygon points="{points}" fill="black" opacity="{0.85 if i.kind=="pad" else 0.65}"><title>{html.escape(i.label+" "+i.net)}</title></polygon>')
    for i in items:
        if i.hole is not None:
            points=' '.join(f'{a:.5f},{b:.5f}' for a,b in i.hole.exterior.coords)
            out.append(f'<polygon points="{points}" fill="white" stroke="black" stroke-width=".02"/>')
    for f in children(b,'footprint'):
        ref=str(props(f).get('Reference',''));px,py=map(float,values(f,'at')[:2])
        if x<=px<=x+w and y<=py<=y+h:
            out.append(f'<rect x="{px-.85}" y="{py-1.3}" width="1.7" height=".8" fill="white"/>')
            out.append(f'<text x="{px}" y="{py-.65}" text-anchor="middle" font-family="sans-serif" font-size=".65" fill="black">{html.escape(ref)}</text>')
    out.append('</svg>');path.write_text('\n'.join(out))

if __name__=='__main__':
    out=ROOT/'verification';out.mkdir(exist_ok=True)
    render(out/'pcb_top_preview.svg',(-1,-1,60,112),900)
    render(out/'u2_escape_preview.svg',(18,45,24,22),1200)
