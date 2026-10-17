#!/usr/bin/env python3
"""Audit the USB candidate geometry, not impedance, propagation delay or hardware operation.

Path lengths include nominal board thickness for F/B vias. Coupling is a sampled
centerline-distance proxy, not electromagnetic extraction. Run native DRC separately.
"""
import heapq,math,json
from pathlib import Path
from collections import defaultdict
BASE = Path(__file__).resolve().parents[1]
from finish_power_routes import Router,rb
from plane_connectivity import zones,connected_groups
from kicad_sexpr import children,val,values
from shapely.geometry import LineString,Point
from shapely.ops import unary_union,nearest_points

# Geometry contract (2026-10-15): JLC04101H-3313 stackup, USB 90 ohm edge-coupled microstrip
# w=0.127 mm, s=0.140 mm -> centre pitch 0.267 mm; window -0.005/+0.020 mm covers mitred 45-degree corners.
PAIR_PITCH_MIN=0.262
PAIR_PITCH_MAX=0.287
def graph_metrics(path):
 b=rb.load(path);r=Router(b);thick=float(val(children(b,'general')[0],'thickness'));report={};paths={}
 for net in ['USB_DP','USB_DM']:
  tracks=[i for i in r.items if i.net==net and i.kind=='track'];pads=[i for i in r.items if i.net==net and i.kind=='pad'];vias=[i for i in r.items if i.net==net and i.kind=='via'];g=defaultdict(dict)
  lines={layer:unary_union([LineString(i.pos) for i in tracks if layer in i.layers]) for layer in ['F.Cu','B.Cu']}
  def key(xy,layer):return (round(xy[0],4),round(xy[1],4),layer)
  def edge(a,c,d):g[a][c]=min(d,g[a].get(c,1e99));g[c][a]=min(d,g[c].get(a,1e99))
  for layer,geom in lines.items():
   if geom.is_empty:continue
   parts=[geom] if geom.geom_type=='LineString' else list(geom.geoms)
   anchors=[(i.pos,i) for i in vias]+[(i.pos,i) for i in pads if layer in i.layers]
   for line in parts:
    tt={0.,line.length}
    for xy,it in anchors:
     if Point(xy).distance(line)<.00015:tt.add(line.project(Point(xy)))
    tt=sorted(tt)
    for a,c in zip(tt,tt[1:]):edge(key(line.interpolate(a).coords[0],layer),key(line.interpolate(c).coords[0],layer),c-a)
  for pad in pads:
   k=key(pad.pos,'F.Cu')
   if k not in g:
    raise AssertionError(('pad center not in trace graph',pad.ref,pad.pin,path))
  for via in vias:edge(key(via.pos,'F.Cu'),key(via.pos,'B.Cu'),thick)
  def shortest(src,dst):
   a=key(next(i.pos for i in pads if (i.ref,str(i.pin))==src),'F.Cu');target=key(next(i.pos for i in pads if (i.ref,str(i.pin))==dst),'F.Cu');dist={a:0};prev={};h=[(0,a)]
   while h:
    d,n=heapq.heappop(h)
    if d>dist[n]+1e-9:continue
    if n==target:break
    for other,ln in g[n].items():
     if d+ln<dist.get(other,1e99):dist[other]=d+ln;prev[other]=n;heapq.heappush(h,(d+ln,other))
   assert target in dist,('open path',src,dst)
   pts=[target]
   while pts[-1]!=a:pts.append(prev[pts[-1]])
   pts.reverse();vl=sum(1 for a,c in zip(pts,pts[1:]) if a[2]!=c[2]);length=dist[target]
   return {'planar_mm':length-vl*thick,'via_transitions':vl,'with_nominal_board_thickness_mm':length},pts
  cpu=('U2','76' if net=='USB_DP' else '77');esd=('U9','3' if net=='USB_DP' else '1')
  netreport={'total_planar_copper_mm':sum(LineString(i.pos).length for i in tracks),'vias':len(vias),'layers':sorted({l for i in tracks for l in i.layers}),'paths':{}}
  for dest in [('J1','A6' if net=='USB_DP' else 'A7'),('J1','B6' if net=='USB_DP' else 'B7'),esd]:
   rec,pts=shortest(cpu,dest);netreport['paths']['.'.join(dest)]=rec
   if dest==esd:paths[net]=LineString([q[:2] for q in pts])
  allowed_ends={key(i.pos,'F.Cu') for i in pads}
  assert all(len(neighbors)!=1 or n in allowed_ends for n,neighbors in g.items()), 'Unterminated USB track stub'
  report[net]=netreport
 report['nominal_board_thickness_mm']=thick
 report['orientation_skew_mm']={orientation:abs(report['USB_DP']['paths']['J1.'+orientation+'6']['with_nominal_board_thickness_mm']-report['USB_DM']['paths']['J1.'+orientation+'7']['with_nominal_board_thickness_mm']) for orientation in ['A','B']}
 report['trunk_coupling_fraction_within_0_270mm']={}
 for net,other in [('USB_DP','USB_DM'),('USB_DM','USB_DP')]:
  line=paths[net];n=math.ceil(line.length/.02);d=[line.interpolate((i+.5)*line.length/n).distance(paths[other]) for i in range(n)];report['trunk_coupling_fraction_within_0_270mm'][net]=sum(PAIR_PITCH_MIN<q<PAIR_PITCH_MAX for q in d)/n
 return report


def inspect(board_path):
 import hashlib
 from kicad_sexpr import props
 problems=[];b=rb.load(board_path);r=Router(b)
 expected={'U2':{'76':'USB_DP','77':'USB_DM'},'U9':{'1':'USB_DM','2':'GND','3':'USB_DP','4':'USB_DP','5':'VBUS','6':'USB_DM'},'J1':{'A6':'USB_DP','B6':'USB_DP','A7':'USB_DM','B7':'USB_DM'}}
 actual={f'{i.ref}.{i.pin}':i.net for i in r.items if i.kind=='pad'}
 u9=next(fp for fp in children(b,'footprint') if props(fp).get('Reference')=='U9')
 if props(u9).get('Value')!='USBLC6-2SC6' or 'dnp' in values(u9,'attr'):problems.append('USBLC6-2SC6 must remain fitted; revalidate another protection device')
 for ref,pins in expected.items():
  for pin,net in pins.items():
   if actual.get(f'{ref}.{pin}')!=net:problems.append(f'Pin mapping mismatch: {ref}.{pin}')
 for i in r.items:
  if i.net not in {'USB_DP','USB_DM'}:continue
  if i.kind=='track' and abs(float(val(i.node,'width'))-.127)>1e-6:problems.append('USB track width changed; recalculate the geometry contract')
  if i.kind=='via' and (abs(float(val(i.node,'size'))-.6)>1e-6 or abs(float(val(i.node,'drill'))-.3)>1e-6):problems.append('USB via dimensions changed')
 metrics={}
 try:
  metrics=graph_metrics(board_path)
  if abs(metrics['nominal_board_thickness_mm']-1.)>1e-6:problems.append('Nominal board thickness changed; requalify via path estimates')
  if max(metrics['orientation_skew_mm'].values())>1.:problems.append('Either orientation exceeds the 1 mm nominal geometric path mismatch target')
  if min(metrics['trunk_coupling_fraction_within_0_270mm'].values())<.90:problems.append('Less than 90% of either CPU-to-ESD route has a partner centerline within %.3f-%.3f mm (coupled 0.127/0.140 on JLC04101H-3313)'%(PAIR_PITCH_MIN,PAIR_PITCH_MAX))
  if metrics['USB_DP']['vias']!=0 or metrics['USB_DM']['vias']!=2:problems.append('Unexpected USB via count')
  if metrics['USB_DP']['layers']!=['F.Cu'] or metrics['USB_DM']['layers']!=['B.Cu','F.Cu']:problems.append('Unexpected USB routing layers')
 except (AssertionError,ValueError,KeyError) as e:problems.append(str(e))
 # A 0.44 mm disk excludes only the expected antipad at each USB signal via.
 # This checks reference-plane centerline coverage, not the full return-current field.
 zz=zones(b);via_windows=unary_union([Point(i.pos).buffer(.44) for i in r.items if i.kind=='via' and i.net in {'USB_DP','USB_DM'}]);coverage=[]
 for net in ['USB_DP','USB_DM']:
  for layer,ref in [('F.Cu','In1.Cu'),('B.Cu','In2.Cu')]:
   line=unary_union([LineString(i.pos) for i in r.items if i.kind=='track' and i.net==net and layer in i.layers]);ground=unary_union([i.geom for i in zz if i.net=='GND' and ref in i.layers]);missing=line.difference(ground.union(via_windows)).length
   coverage.append({'net':net,'signal_layer':layer,'reference_layer':ref,'centerline_mm':line.length,'uncovered_centerline_outside_via_antipads_mm':missing})
   if missing>1e-5:problems.append(f'{net} {layer}: reference-ground gap')
 branch=sum(LineString(i.pos).length for i in r.items if i.kind=='track' and i.net=='USB_DM' and 'B.Cu' in i.layers)
 if branch>1.2:problems.append('USB duplicate-contact back-layer branch exceeds 1.2 mm')
 return {'static_checks_passed':not problems,'board_sha256':hashlib.sha256(board_path.read_bytes()).hexdigest(),'metrics':metrics,'reference_coverage':coverage,'back_branch_planar_mm':branch,'problems':problems,'impedance_verified':False,'hardware_verified':False,'fabrication_released':False}


if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--board',type=Path,default=BASE/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb');ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 result=inspect(args.board);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['static_checks_passed'] else 1)
