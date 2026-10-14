"""Read-only geometric evidence; supplements native DRC, not an SI/PI solver.

Run with the reviewed repository's Python requirements plus Pillow installed.
The board argument may be the saved, natively refilled audit copy.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--board', type=Path, required=True)
ap.add_argument('--original', type=Path, required=True)
ap.add_argument('--tools', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
sys.path.insert(0, str(args.tools))
from plane_connectivity import zones, connected_groups
from geometry_audit import board_items
import kicad_sexpr as s
from PIL import Image, ImageDraw, ImageFont

board = s.load(args.board)
original = s.load(args.original)
items = board_items(board)
physical = items + zones(board)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def normalized(node):
    if isinstance(node, list):
        return [normalized(value) for value in node]
    if isinstance(node, str) and not isinstance(node, s.Q) and re.fullmatch(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', node):
        return float(node)
    return node
source_objects = lambda tree, kind: sorted(json.dumps(normalized(n)) for n in s.children(tree, kind))
semantic = {kind: source_objects(board, kind) == source_objects(original, kind)
            for kind in ['footprint', 'segment', 'via', 'arc', 'gr_line', 'gr_arc']}
net_names = sorted({i.net for i in items if i.kind == 'pad' and i.net and not i.net.startswith('unconnected-')})
groups = {}
for net in net_names:
    groups[net] = [sorted(i.label for i in group if i.kind == 'pad')
                   for group in connected_groups([i for i in physical if i.net == net])
                   if any(i.kind == 'pad' for i in group)]
unconnected = {net: group for net, group in groups.items() if len(group) != 1}
hits = []
for via in (i for i in items if i.kind == 'via'):
    for pad in (i for i in items if i.kind == 'pad' and i.hole is None and i.layers):
        if via.hole.distance(pad.geom) < 1e-9:
            hits.append({'via': via.label, 'pos_mm': via.pos, 'pad': pad.label, 'net': pad.net,
                         'drill_overlap_area_mm2': via.hole.intersection(pad.geom).area})
selected = ['DSI_CKN','DSI_CKP','DSI_D0N','DSI_D0P','SD_CLK','XIN','XOUT',
            'USB_DP','USB_DM','FEL_KEY_N','FEL_N']
metrics = {}
for net in selected:
    tracks = [i for i in items if i.kind == 'track' and i.net == net]
    metrics[net] = {'total_segment_length_mm': sum(math.dist(*i.pos) for i in tracks),
                    'layers': sorted({layer for i in tracks for layer in i.layers}),
                    'vias': sum(i.kind == 'via' and i.net == net for i in items),
                    'widths_mm': sorted({float(s.val(i.node, 'width')) for i in tracks})}
ref_positions = {s.props(f)['Reference']: s.values(f, 'at') for f in s.children(board, 'footprint')}
report = {'original_board_sha256': sha(args.original), 'analyzed_board_sha256': sha(args.board),
          'method': 'Saved native refill, 2D copper intersection at 1e-6 mm tolerance; pad-bearing same-net groups only. No impedance, current, timing, or hardware inference.',
          'original_vs_refilled_objects_unchanged': semantic,
          'objects': dict(Counter(i.kind for i in items)), 'physical_net_count': len(net_names),
          'pad_groups': groups, 'disconnected_pad_groups': unconnected,
          'via_in_pad_pair_count': len(hits), 'via_in_pad_unique_vias': len({h['via'] for h in hits}),
          'via_in_pad_includes_tangencies': True, 'signal_metrics': metrics,
          'in2_segment_length_mm': sum(math.dist(*i.pos) for i in items if i.kind == 'track' and 'In2.Cu' in i.layers),
          'footprint_positions_mm_degrees': ref_positions}
args.output.mkdir(parents=True, exist_ok=True)
(args.output/'geometry_audit.json').write_text(json.dumps(report, indent=2)+'\n')
(args.output/'via_in_pad_audit.json').write_text(json.dumps({'analyzed_board_sha256': sha(args.board), 'intersections': hits}, indent=2)+'\n')

# Geometry-derived overview images: no visual alteration of source copper.
font_path = '/System/Library/Fonts/Monaco.ttf'
font = ImageFont.truetype(font_path, 15)
small = ImageFont.truetype(font_path, 12)
palette = ['#f5576c', '#4ea6ff', '#f6b44c', '#51d4a4', '#bc93ff', '#dddd66']
views = [
    ('usb', 'USB: current F.Cu and B.Cu copper', ['USB_DP','USB_DM'], ['J1','U9','U2']),
    ('mipi', 'MIPI: current F.Cu copper', ['DSI_CKN','DSI_CKP','DSI_D0N','DSI_D0P'], ['U2','J4']),
    ('fel', 'FEL: incomplete copper; circles = DRC findings', ['FEL_KEY_N','FEL_N','BOOT0','BOOT1'], ['U2','R33','R34','SW6','J3']),
    ('power', 'Power: current copper, all four layers projected', ['VSYS','3V3','CORE_0V93','DRAM_1V5','1V8','RTC_3V3'], ['U1','U2','L1','L2','L3','U10','J1','J2']),
]
def polygons(geom):
    if geom.geom_type == 'Polygon': return [geom]
    return [p for p in getattr(geom, 'geoms', []) if p.geom_type == 'Polygon']
for filename, title, nets, labels in views:
    focus = [i for i in items if i.net in nets]
    bounds = [i.geom.bounds for i in focus]
    x0,y0 = min(b[0] for b in bounds)-1.2, min(b[1] for b in bounds)-1.2
    x1,y1 = max(b[2] for b in bounds)+1.2, max(b[3] for b in bounds)+1.2
    scale = min(40, 1100/(x1-x0), 1350/(y1-y0))
    width,height = max(900,int((x1-x0)*scale)+100),int((y1-y0)*scale)+160
    im = Image.new('RGB', (width,height), '#131c29'); draw = ImageDraw.Draw(im)
    def xy(p): return (50+(p[0]-x0)*scale, 100+(p[1]-y0)*scale)
    colors = dict(zip(nets,palette))
    for i in sorted(items,key=lambda obj: obj.net in colors):
        if i.geom.bounds[2]<x0 or i.geom.bounds[0]>x1 or i.geom.bounds[3]<y0 or i.geom.bounds[1]>y1: continue
        if filename in ['usb','mipi','fel'] and not i.layers & {'F.Cu','B.Cu'}: continue
        for polygon in polygons(i.geom):
            draw.polygon([xy(p) for p in polygon.exterior.coords],fill=colors.get(i.net,'#303b4c'))
        if i.kind=='via' and i.net in colors:
            x,y=xy(i.pos);draw.ellipse((x-2,y-2,x+2,y+2),fill='#131c29')
    for ref in labels:
        if ref in ref_positions:
            x,y=xy(tuple(map(float,ref_positions[ref][:2])))
            if 0<x<width-60 and 75<y<height-30:
                draw.text((x+5,y-18),ref,font=font,fill='white',stroke_width=2,stroke_fill='#131c29')
    if filename=='fel':
        drc=json.loads((args.output/'drc.json').read_text())
        for finding in drc['violations']+drc['unconnected_items']:
            for item in finding.get('items',[]):
                p=item.get('pos',{});x,y=xy((p.get('x',0),p.get('y',0)))
                draw.ellipse((x-9,y-9,x+9,y+9),outline='#ffffff',width=2)
    draw.rectangle((0,0,width,85),fill='#131c29')
    draw.text((20,15),title,font=font,fill='white')
    for idx,net in enumerate(nets):
        draw.text((20+(idx%3)*280,40+(idx//3)*20),net,font=small,fill=palette[idx])
    draw.rectangle((0,height-45,width,height),fill='#131c29')
    draw.text((20,height-35),'Derived geometry overview; see native DRC and JSON for measurements.',font=small,fill='#aebed0')
    im.save(args.output/(filename+'_copper.png'))
print(json.dumps({k:v for k,v in report.items() if k in ['physical_net_count','disconnected_pad_groups','original_vs_refilled_objects_unchanged','via_in_pad_pair_count','via_in_pad_unique_vias','signal_metrics']},indent=2))
