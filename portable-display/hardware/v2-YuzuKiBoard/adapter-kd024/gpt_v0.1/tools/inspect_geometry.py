from geometry import *
import itertools,json
b=load(); P=b['parts'];pads=b['pads'];ps=[pad_shape(p) for p in pads]
r={'note':'Static geometry only. NOT KiCad DRC; zone fill/thermal relief/manufacturer rules are not validated.','body_collisions':[],'header_clearance':[],'hole_clearance':[],'copper_clearance':[],'via_to_pad':[],'via_in_pad':[],'min_track_width':min(t['width'] for t in b['tracks'])}
for a,c in itertools.combinations([p for p in P if not p['feature']],2):
 sa,sc=body_shape(a,b),body_shape(c,b)
 if sa.intersection(sc).area>.001:r['body_collisions'].append([a['ref'],c['ref'],round(sa.intersection(sc).area,5)])
 if a['ref'].startswith('H') or c['ref'].startswith('H'):
  h,o=(a,c) if a['ref'].startswith('H') else (c,a)
  if not o['ref'].startswith('H'):
   dist=body_shape(h,b).distance(body_shape(o,b))
   if dist<1.5-1e-5:r['header_clearance'].append([h['ref'],o['ref'],round(dist,5)])
for p in P:
 if p['ref'].startswith('MH'):continue
 s=body_shape(p,b)
 for i,(x,y,dr,kr) in enumerate(b['holes'],1):
  d=s.distance(Point(x,y))-dr
  if d<1.5-1e-5:r['hole_clearance'].append([p['ref'],f'MH{i}',round(d,5)])
for v in b['vias']:
 s=via_shape(v)
 for p,g in zip(pads,ps):
  d=s.distance(g)
  if d<.15-1e-5:r['via_to_pad'].append([v['net'],[v['x'],v['y']],p['ref']+':'+p['num'],round(d,5)])
  if s.intersects(g):r['via_in_pad'].append([v['net'],p['ref']+':'+p['num']])
# copper clearance, per conducting layer. Different net only, including NC copper islands.
for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']:
 items=[]
 for p,g in zip(pads,ps):
  if p['kind']=='np_thru_hole':continue
  if layer=='F.Cu' or p['kind']=='thru_hole':items.append((p['net'] or f"NC_{p['ref']}_{p['num']}",p['ref']+':'+p['num'],g))
 items += [(v['net'],f"via@{v['x']},{v['y']}",via_shape(v)) for v in b['vias']]
 items += [(t['net'],f'track{i}',track_shape(t)) for i,t in enumerate(b['tracks']) if t['layer']==layer]
 for (n,ref,g),(nn,rr,gg) in itertools.combinations(items,2):
  if n==nn:continue
  ax,ay,bx,by=g.bounds;cx,cy,dx,dy=gg.bounds
  if ax>dx+.15 or cx>bx+.15 or ay>dy+.15 or cy>by+.15:continue
  d=g.distance(gg)
  if d<.15-1e-5:r['copper_clearance'].append([layer,ref,rr,n,nn,round(d,5)])
(ROOT/'reports/static_geometry.json').write_text(json.dumps(r,indent=2))
for k,v in r.items():print(k,len(v) if isinstance(v,list) else v)
for k in ['body_collisions','header_clearance','hole_clearance','via_to_pad','copper_clearance']:
 print(k,r[k][:20])
