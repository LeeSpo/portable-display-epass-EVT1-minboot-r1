#!/usr/bin/env python3
"""Export *review-only* CAM, BOM, CPL directly from the written KiCad board.
The exporter is custom, not kicad-cli. Ground-zone cache is algorithmic and
must be replaced/refilled and DRC-checked in KiCad before fabrication release.
"""
from geometry import *
from native_io import *
from shapely import constrained_delaunay_triangles
import csv,zipfile,hashlib,math,json
outdir=ROOT/'manufacturing';outdir.mkdir(exist_ok=True)
b=load();p=read_pcb();tree=p['tree'];cu=['F.Cu','In1.Cu','In2.Cu','B.Cu'];fills={};triangles={}
# Prove export inputs and source model agree, including connector centroid rebasing.
assert {a['ref'] for a in p['parts']}=={a['ref'] for a in b['parts']}
assert len(p['tracks'])==len(b['tracks']) and len(p['vias'])==len(b['vias'])
for a in b['pads']:
 z=next(z for z in p['pads'] if z['ref']==a['ref'] and z['num']==a['num'] and z['kind']==a['kind'] and ('F.Cu' in z['layers'] or '*.Cu' in z['layers']))
 assert math.dist((a['x'],a['y']),(z['x'],z['y']))<1e-5,(a,z)
# Complete native-zone cache by fracturing exact polygonal fill into triangles.
for z in p['zones']:
 layer=z['layer'];obs=[]
 for a in p['pads']:
  copper=layer in a['layers'] or '*.Cu' in a['layers']
  if a['kind']=='np_thru_hole':obs.append(Point(a['x'],a['y']).buffer(a['drill']/2+1.5,quad_segs=32))
  elif copper and a['net']!='GND':obs.append(pad_shape(a).buffer(.15,quad_segs=8))
 for v in p['vias']:
  if v['net']!='GND':obs.append(via_shape(v).buffer(.15,quad_segs=8))
 for t in p['tracks']:
  if t['net']!='GND' and t['layer']==layer:obs.append(track_shape(t).buffer(.15,quad_segs=8))
 g=z['shape'].difference(unary_union(obs)).buffer(0)
 # Remove isolated copper regions that touch no GND pad, via or routed GND link.
 seeds=[]
 for a in p['pads']:
  if a['net']=='GND' and (layer in a['layers'] or '*.Cu' in a['layers']):seeds.append(pad_shape(a))
 seeds += [via_shape(v) for v in p['vias'] if v['net']=='GND']
 seeds += [track_shape(t) for t in p['tracks'] if t['net']=='GND' and t['layer']==layer]
 seed=unary_union(seeds)
 g=unary_union([pp for pp in polys(g) if pp.intersects(seed)])
 fills[layer]=g
 tris=[tt for pp in polys(g) for tt in constrained_delaunay_triangles(pp).geoms]
 triangles[layer]=tris
 node=z['node'];node[:]=[x for x in node if not(isinstance(x,list) and x and x[0] in ['filled_polygon','filled_areas_thickness'])]
 node.append([Atom('filled_areas_thickness'),Atom('no')])
 for tt in tris:
  node.append([Atom('filled_polygon'),[Atom('layer'),layer],[Atom('pts')]+[[Atom('xy'),round(x,6),round(y,6)] for x,y in list(tt.exterior.coords)[:-1]]])
 print('Zone',layer,'area',round(g.area,2),'triangles',len(tris))
# Saved native PCB is now the one source revision for every manufacturing file.
boardpath=ROOT/'kicad/adapter_v0.1.kicad_pcb';boardpath.write_text(dump(tree))
boardhash=hashlib.sha256(boardpath.read_bytes()).hexdigest()
(ROOT/'reports/zone_geometry.json').write_text(json.dumps({k:v.wkt for k,v in fills.items()}))
# One polygon-based Gerber region primitive for every land / trace / zone triangle.
# No aperture macro support is needed: closed polygonal regions are standard RS-274X.
def coords(pt):return (int(round((pt[0]-50)*1e6)),int(round((82-pt[1])*1e6)))
def gerber(name,shapes,comment):
 lines=['G04 ENGINEERING HOLD - DO NOT FABRICATE*','G04 '+comment+'*','G04 PCB SHA256 '+boardhash+'*','%FSLAX46Y46*%','%MOMM*%','%LPD*%','%ADD10C,0.010000*%','D10*','G01*']
 count=0
 for g in shapes:
  for pp in polys(g):
   # Shapes here are triangles / convex flashes / stroke polygons. Split holes if any.
   seq=list(constrained_delaunay_triangles(pp).geoms) if pp.interiors else [pp]
   for po in seq:
    xy=[coords(c) for c in po.exterior.coords]
    lines += ['G36*',f'X{xy[0][0]}Y{xy[0][1]}D02*']+[f'X{x}Y{y}D01*' for x,y in xy[1:]]+['G37*'];count+=1
 lines.append('M02*');(outdir/name).write_text('\n'.join(lines)+'\n');return count
manifest=[]
for layer,ext in zip(cu,['GTL','G1','G2','GBL']):
 shapes=list(triangles[layer])
 for a in p['pads']:
  if a['kind']!='np_thru_hole' and (layer in a['layers'] or '*.Cu' in a['layers']):shapes.append(pad_shape(a))
 shapes += [via_shape(v) for v in p['vias']]+[track_shape(t) for t in p['tracks'] if t['layer']==layer]
 name='adapter_v0.1_'+layer.replace('.','_')+'.'+ext
 manifest.append({'file':name,'layer':layer,'regions':gerber(name,shapes,layer)})
for layer,ext in [('F.Mask','GTS'),('B.Mask','GBS'),('F.Paste','GTP')]:
 shapes=[]
 for a in p['pads']:
  if layer in a['layers'] or (layer.endswith('Mask') and '*.Mask' in a['layers']):
   g=pad_shape(a)
   if layer.endswith('Mask') and a['kind']!='np_thru_hole' and not a['ref'].startswith('FID'):g=g.buffer(.05,quad_segs=8)
   shapes.append(g)
 name='adapter_v0.1_'+layer.replace('.','_')+'.'+ext
 manifest.append({'file':name,'layer':layer,'regions':gerber(name,shapes,layer+'; vias tented; check native mask settings before release')})
# Silkscreen includes native lines, dots, and vectorized native text.
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from shapely.affinity import scale as gscale
sil=[]
for s in p['silk']:
 if s['kind']=='line':sil.append(LineString([s['a'],s['b']]).buffer(s['width']/2,quad_segs=8))
 elif s['kind']=='circle':sil.append(Point(*s['c']).buffer(s['r']+s['width']/2,quad_segs=16))
 else:
  tp=TextPath((0,0),s['text'],size=s['size'],prop=FontProperties(family='DejaVu Sans'))
  outlines=[Polygon(poly) for poly in tp.to_polygons() if len(poly)>2]
  if outlines:
   g=outlines[0]
   # Alternating contours are combined with symmetric difference to preserve glyph holes.
   for gg in outlines[1:]:g=g.symmetric_difference(gg)
   xa,ya,xb,yb=g.bounds;g=translate(gscale(g,xfact=1,yfact=-1,origin=(0,0)),s['at'][0]-(xa+xb)/2,s['at'][1]+(ya+yb)/2)
   sil.append(g)
for layer,ext,shapes in [('F.SilkS','GTO',sil),('B.SilkS','GBO',[])]:
 name='adapter_v0.1_'+layer.replace('.','_')+'.'+ext;manifest.append({'file':name,'layer':layer,'regions':gerber(name,shapes,layer+'; bottom intentionally blank, all components on Top')})
# Outline uses a single closed zero-width mathematical path with a 0.05 mm plot aperture.
lines=['G04 ENGINEERING HOLD - DO NOT FABRICATE*','G04 PCB SHA256 '+boardhash+'*','%FSLAX46Y46*%','%MOMM*%','%ADD10C,0.050000*%','D10*','G01*']
for i,t in enumerate(p['edge']):
 a,c=coords(t['a']),coords(t['b'])
 if i==0:lines.append(f'X{a[0]}Y{a[1]}D02*')
 lines.append(f'X{c[0]}Y{c[1]}D01*')
assert p['edge'][-1]['b']==p['edge'][0]['a']
lines.append('M02*');(outdir/'adapter_v0.1_Edge_Cuts.GKO').write_text('\n'.join(lines)+'\n')
manifest.append({'file':'adapter_v0.1_Edge_Cuts.GKO','layer':'Edge.Cuts','closed_paths':1})
# Separate PTH and NPTH; common lower-left auxiliary origin, decimal mm.
for plated in [True,False]:
 holes=[]
 for a in p['pads']:
  if a.get('drill') and ((a['kind']=='thru_hole')==plated):holes.append((a['drill'],a['x'],a['y']))
 if plated:holes += [(v['drill'],v['x'],v['y']) for v in p['vias']]
 sizes=sorted({h[0] for h in holes});di={d:i+1 for i,d in enumerate(sizes)}
 lines=['M48','; ENGINEERING HOLD - DO NOT FABRICATE','; PCB SHA256 '+boardhash,'METRIC,TZ']+[f'T{di[d]:02d}C{d:.3f}' for d in sizes]+['%','G90','G05']
 for d in sizes:
  lines.append(f'T{di[d]:02d}')
  lines += [f'X{x-50:.6f}Y{82-y:.6f}' for dd,x,y in holes if dd==d]
 lines += ['M30'];name='adapter_v0.1_'+('PTH' if plated else 'NPTH')+'.drl';(outdir/name).write_text('\n'.join(lines)+'\n');manifest.append({'file':name,'plated':plated,'holes':len(holes),'units':'mm'})
# Assembly deliverables, directly from native footprint attributes and origins.
def writecsv(path,head,rows):
 with open(path,'w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(head);w.writerows(rows)
fit=[a for a in p['parts'] if not a['dnp'] and not a['feature']];dnp=[a for a in p['parts'] if a['dnp']];features=[a for a in p['parts'] if a['feature']]
writecsv(outdir/'adapter_v0.1_bom.csv',['Comment','Designator','Footprint','LCSC'],[[a['value'],a['ref'],a['footprint'],a['props'].get('LCSC','')] for a in fit])
writecsv(outdir/'adapter_v0.1_bom_dnp.csv',['Comment','Designator','Footprint','LCSC'],[['\u4e0d\u8d34 / '+a['value'],a['ref'],a['footprint'],a['props'].get('LCSC','')] for a in dnp])
writecsv(outdir/'adapter_v0.1_cpl.csv',['Designator','Mid X','Mid Y','Layer','Rotation'],[[a['ref'],f'{a["x"]-50:.6f}',f'{82-a["y"]:.6f}','Top',f'{a["angle"]:.3f}'] for a in fit])
writecsv(outdir/'copper_and_mechanical_features.csv',['Designator','Comment','X_mm','Y_mm','Reason'],[[a['ref'],a['value'],a['x']-50,82-a['y'],'No purchased component; excluded from BOM/CPL'] for a in features])
manifest_data={'status':'ENGINEERING_REVIEW_ONLY_DO_NOT_FABRICATE','native_kicad_erc_drc_run':False,'fabrication_released':False,'pcb_sha256':boardhash,'exporter':'tools/export_review.py (custom, not kicad-cli)','source_pcb':'kicad/adapter_v0.1.kicad_pcb','origin_pcb_mm':[50,82],'CAM_X':'pcb_x - 50','CAM_Y':'82 - pcb_y','units':'mm','smt_fitted_count':len(fit),'dnp_count':len(dnp),'copper_feature_count':len(features),'files':manifest}
(outdir/'CAM_MANIFEST.json').write_text(json.dumps(manifest_data,indent=2))
(outdir/'DO_NOT_FABRICATE.txt').write_text('ENGINEERING REVIEW ONLY. FOUR DSI NETS HAVE NO COPPER ROUTES.\nSpecified JLC impedance result unavailable; native KiCad ERC/DRC NOT RUN.\nDo not upload this archive for manufacture or assembly. See DESIGN_NOTES.md.\nAll included data is from the board SHA-256 recorded in CAM_MANIFEST.json.\n')
with zipfile.ZipFile(outdir/'adapter_v0.1_gerber.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for a in manifest:z.write(outdir/a['file'],a['file'])
 for name in ['CAM_MANIFEST.json','DO_NOT_FABRICATE.txt']:z.write(outdir/name,name)
print('Exported review CAM / BOM / CPL from',boardhash,'fitted',len(fit),'DNP',len(dnp))
