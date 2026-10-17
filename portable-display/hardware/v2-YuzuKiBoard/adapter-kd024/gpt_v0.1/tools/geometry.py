from __future__ import annotations
import math, json, pathlib
from shapely.geometry import Point, Polygon, box, LineString
from shapely.affinity import rotate, translate
from shapely.ops import unary_union
ROOT=pathlib.Path(__file__).resolve().parents[1]
def load():return json.loads((ROOT/'reports/design_model.json').read_text())
def save(b): (ROOT/'reports/design_model.json').write_text(json.dumps(b,indent=2))
def pad_shape(p):
 if p['shape']=='circle':return Point(p['x'],p['y']).buffer(p['w']/2,quad_segs=16)
 g=box(-p['w']/2,-p['h']/2,p['w']/2,p['h']/2)
 return translate(rotate(g,-p.get('angle',0),origin=(0,0)),p['x'],p['y'])
def body_shape(p,b,margin=0):
 a=b['footprints'][p['footprint']]['body'];g=box(*a)
 return translate(rotate(g,-p['angle'],origin=(0,0)),p['x'],p['y']).buffer(margin,join_style=2)
def track_shape(t):return LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=8)
def via_shape(v):return Point(v['x'],v['y']).buffer(v.get('size',.6)/2,quad_segs=12)
def polys(g):
 if g.is_empty:return []
 if g.geom_type=='Polygon':return [g]
 return [p for x in getattr(g,'geoms',[]) for p in polys(x)]
def trans(p,x,y):
 a=math.radians(p['angle']);return p['x']+x*math.cos(a)+y*math.sin(a),p['y']-x*math.sin(a)+y*math.cos(a)
