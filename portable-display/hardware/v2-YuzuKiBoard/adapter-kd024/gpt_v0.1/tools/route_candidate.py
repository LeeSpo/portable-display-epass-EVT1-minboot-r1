#!/usr/bin/env python3
"""Grid clearance router for review; not a substitute for KiCad DRC or SI review.
Never routes DSI: actual JLC calculator result is a hard input to a later revision.
"""
import sys, math, json, ctypes, pathlib
import numpy as np
from PIL import Image, ImageDraw
from geometry import *
b=load(); b['tracks']=[];b['vias']=[]
pads=b['pads'];shapes=[pad_shape(p) for p in pads]
board=box(*b['board']); keep=[Point(x,y).buffer(r,quad_segs=32) for x,y,d,r in b['holes']]
by={p['ref']+':'+p['num']:p for p in pads}
pol=board.buffer(-.3)
def addtrack(net,a,c,width=.15,layer='F.Cu'):
 if math.dist(a,c)>1e-7:b['tracks'].append({'net':net,'a':[round(v,6) for v in a],'b':[round(v,6) for v in c],'width':width,'layer':layer})
def addvia(net,x,y,source='router'):
 for v in b['vias']:
  if math.dist((x,y),(v['x'],v['y']))<.05 and v['net']==net:return
 b['vias'].append({'net':net,'x':round(x,6),'y':round(y,6),'size':.6,'drill':.3,'source':source})
def validvia(x,y,net):
 g=Point(x,y).buffer(.3,quad_segs=12)
 if not pol.covers(g):return False
 if any(g.intersects(k) for k in keep):return False
 if any(g.distance(s)<.15001 for s in shapes):return False
 if any(math.dist((x,y),(v['x'],v['y'])) < (.55 if v['net']==net else .75) for v in b['vias']):return False
 return True
# Individual adjacent vias for each J1 ground contact, including mounting pads.
fan=[]
for p in pads:
 if p['net']!='GND' or p['kind']!='smd':continue
 if p['ref']=='J2' and not p['num'].startswith('MP'):continue
 if p['ref']=='J1':
  if p['num'].startswith('MP'):
   x=p['x']+(-.9 if p['num']=='MP1' else .9);y=p['y']
  else:x=p['x'];y=p['y']-1.15
  if validvia(x,y,'GND'):
   addvia('GND',x,y,'J1_'+p['num']);addtrack('GND',(p['x'],p['y']),(x,y),.2);fan.append((p['ref'],p['num'],x,y));continue
 # Search a non-via-in-pad fanout. The short F.Cu link is checked against foreign pads.
 candidates=[]
 for rr in [1.,1.1,1.2,1.35,1.5,1.7,2.0,2.4]:
  for a in range(0,360,30):
   x=round(p['x']+rr*math.cos(math.radians(a)),3);y=round(p['y']+rr*math.sin(math.radians(a)),3)
   if not validvia(x,y,'GND'):continue
   tr=LineString([(p['x'],p['y']),(x,y)]).buffer(.10,quad_segs=8)
   if any(tr.distance(s)<.15 for pp,s in zip(pads,shapes) if pp['net']!='GND'):continue
   if any(tr.intersects(k) for k in keep):continue
   candidates.append((rr,x,y));break
  if candidates:break
 if candidates:
  rr,x,y=candidates[0];addvia('GND',x,y,p['ref']+'_'+p['num']);addtrack('GND',(p['x'],p['y']),(x,y),.20);fan.append((p['ref'],p['num'],x,y))
# J2-5 is enclosed by the bias escapes; connect its otherwise isolated island
# to In1 with an edge-side via. Clearance to pad edge is 0.165 mm.
assert validvia(81.9,44.6,'GND')
addvia('GND',81.9,44.6,'J2_5_ground_island_fix')
addtrack('GND',(81.9,45.4),(81.9,44.6),.15)
fan.append(('J2','5',81.9,44.6))
# Additional ground-fence candidate rows alongside the reserved DSI corridor.
for x in [67.7,74.1]:
 for y in [57.5,60.5,63.5,66.5,69.5,72.5,74.5]:
  if validvia(x,y,'GND'):addvia('GND',x,y,'DSI_corridor_fence')
# Deterministic staggered-row escape for non-DSI panel signals. These short
# top-layer connections are independent of the still-unverified DSI geometry.
j2escape={
 'ELVSS': [([(82.5,45.4),(82.5,46.35)],(82.5,46.35)), ([(82.2,48.465),(82.2,47.5)],(82.2,47.5))],
 'ELVDD': [([(81.6,48.465),(81.6,46.7)],(81.6,46.7)), ([(81.3,45.4),(81.3,46.1),(81.6,46.4),(81.6,46.7)],None)],
 'PANEL_VCI_3V3': [([(80.7,45.4),(80.7,46.4)],(80.7,46.4))],
 'VDDIO_1V8': [([(80.1,45.4),(80.1,47.2)],(80.1,47.2))],
 'PANEL_TE1': [([(79.5,45.4),(79.5,46.4)],(79.5,46.4))],
 'PANEL_SWIRE': [([(79.2,48.465),(79.2,47.4)],(79.2,47.4))],
 'PANEL_TE': [([(78.9,45.4),(78.9,45.85),(78.35,46.4),(78.3,46.4)],(78.3,46.4))],
 'PANEL_RESET_1V8': [([(78.6,48.465),(78.6,47.9),(78.3,47.6),(78.3,47.4)],(78.3,47.4))]
}
for net,esc in j2escape.items():
 for points,v in esc:
  if v:
   if not validvia(*v,net):raise RuntimeError('Invalid J2 escape via '+net+str(v))
   addvia(net,*v,'J2_staggered_escape')
  for a,c in zip(points,points[1:]):addtrack(net,a,c,.15)
# Explicit switching nodes, no vias. Exact clearances are verified after routing.
# Fine escapes are kept away from the DSI corridor; this is not a power-loop signoff.
sw_manual={
 'SWP':[(58.05,63.075),(57.6,63.075),(56.485,61.96),(56.485,61.)],
 'SWN':[(60.95,63.975),(64.95,63.975),(65.1,64.125),(65.1,66.15),(63.4,67.85),(63.4,67.915)]}
# Route all nets with A*, including switching nets if the manual path is obstructed.
step=.05;x0,y0,x1,y1=b['board'];nx=int(round((x1-x0)/step))+1;ny=int(round((y1-y0)/step))+1
layers=['F.Cu','In2.Cu','B.Cu'];N=nx*ny
import subprocess
build_dir=pathlib.Path(__file__).resolve().parent/'.build';build_dir.mkdir(exist_ok=True)
so=build_dir/'route_astar.so'
cpp=pathlib.Path(__file__).resolve().parent/'route_astar.cpp'
if not so.exists() or so.stat().st_mtime < cpp.stat().st_mtime:
 subprocess.run(['g++','-O3','-std=c++17','-shared','-fPIC',str(cpp),'-o',str(so)],check=True)
lib=ctypes.CDLL(str(so))
lib.astar.argtypes=[ctypes.c_int]*3+[ctypes.c_void_p]*2+[ctypes.c_int]*2+[ctypes.c_void_p,ctypes.c_int]
lib.astar.restype=ctypes.c_int

def raster(geoms,fill=1):
 from shapely import contains_xy
 out=np.zeros((ny,nx),dtype=np.uint8)
 for g in geoms:
  if g.is_empty:continue
  xa,ya,xb,yb=g.bounds
  i0=max(0,int(math.floor((xa-x0)/step)));i1=min(nx,int(math.ceil((xb-x0)/step))+1)
  j0=max(0,int(math.floor((ya-y0)/step)));j1=min(ny,int(math.ceil((yb-y0)/step))+1)
  if i0>=i1 or j0>=j1:continue
  xx=x0+np.arange(i0,i1)*step;yy=y0+np.arange(j0,j1)*step
  out[j0:j1,i0:i1] |= contains_xy(g,xx[None,:],yy[:,None]).astype(np.uint8)
 return out
# Avoid forbidden board/NPTH regions; masks are blocked outside the usable shape.
def edge_strips(m):
 return [box(x0,y0,x1,y0+m),box(x0,y1-m,x1,y1),box(x0,y0,x0+m,y1),box(x1-m,y0,x1,y1)]
common=edge_strips(.45)+[k.buffer(.1) for k in keep]
base=[raster(common) for _ in layers]
# All DSI connection pads remain untouched by routing. Reserve a broad corridor
# on F.Cu in the central area; ends must later be escaped and length-tuned manually.
reserve=box(68.3,57.3,73.6,74.7)
base[0]|=raster([reserve])
route_report=[]
def idx(pt,l=0):
 x,y=pt;return l*N+int(round((y-y0)/step))*nx+int(round((x-x0)/step))
def coord(i):
 l=i//N;a=i%N;return (round(x0+(a%nx)*step,6),round(y0+(a//nx)*step,6),l)
def obstacles(net,width):
 out=np.stack([z.copy() for z in base]);infl=.15+width/2+.015
 for li,layer in enumerate(layers):
  gg=[]
  for p,s in zip(pads,shapes):
   if p['net']==net:continue
   if li==0 or p['kind']!='smd':gg.append(s.buffer(infl,quad_segs=6))
  gg += [via_shape(v).buffer(infl,quad_segs=6) for v in b['vias'] if v['net']!=net]
  gg += [track_shape(t).buffer(infl,quad_segs=6) for t in b['tracks'] if t['net']!=net and t['layer']==layer]
  out[li]|=raster(gg)
 viaob=[s.buffer(.47,quad_segs=6) for s in shapes]
 viaob += [Point(v['x'],v['y']).buffer(.77 if v['net']!=net else .55,quad_segs=6) for v in b['vias']]
 viaob += [track_shape(t).buffer(.47,quad_segs=6) for t in b['tracks'] if t['net']!=net]
 viaob += edge_strips(.62)+[k.buffer(.31) for k in keep]+[reserve]
 vok=(raster(viaob)==0).astype(np.uint8)
 for v in b['vias']:
  if v['net']==net:
   ix=int(round((v['x']-x0)/step));iy=int(round((v['y']-y0)/step))
   vok[iy,ix]=1
 return out,vok
# MST over component pads, routed short links first; no DSI copper under any circumstance.
netorder=['SWP','SWN','ELVDD_SENSE','LDO_FB','BIAS_CT','ELVDD','ELVSS','BIAS_IN_3V6','PRE_3V584','VBUS_5V','LOGIC_LDO_IN','VDDIO_1V8','HOST_3V3_LOGIC','PANEL_VCI_3V3','LCD_EN','HOST_RST_3V3','PANEL_RESET_1V8','PANEL_TE1','PANEL_TE','PANEL_SWIRE']
for net in netorder:
 nodes=[p for p in pads if p['net']==net]
 if len(nodes)<2:continue
 used={0};edges=[]
 while len(used)<len(nodes):
  v=min((math.dist((nodes[i]['x'],nodes[i]['y']),(nodes[j]['x'],nodes[j]['y'])),i,j) for i in used for j in range(len(nodes)) if j not in used)
  _,i,j=v;edges.append((i,j));used.add(j)
 widths=[.25,.15] if net in ['SWP','SWN','ELVDD','ELVSS','BIAS_IN_3V6','PRE_3V584','VBUS_5V','PANEL_VCI_3V3'] else [.15]
 for i,j in edges:
  p1,p2=nodes[i],nodes[j];pt1=(p1['x'],p1['y']);pt2=(p2['x'],p2['y']);st,goal=idx(pt1),idx(pt2);success=False
  for width in widths:
   obs,vok=obstacles(net,width)
   if net in ['SWP','SWN','BIAS_CT','LDO_FB','ELVDD_SENSE']:vok[:]=0
   # Through-hole pads can originate on any connected layer, but use Top start here.
   if obs.reshape(-1)[st] or obs.reshape(-1)[goal]:continue
   path=np.zeros(100000,dtype=np.int32)
   n=lib.astar(nx,ny,3,obs.ctypes.data,vok.ctypes.data,st,goal,path.ctypes.data,len(path))
   if n>0:
    pts=[coord(int(v)) for v in path[:n]]
    chain=[(pt1[0],pt1[1],0)]+pts+[(pt2[0],pt2[1],0)]
    # Collapse collinear runs and create through vias only at layer changes.
    run=[]
    def flush(run):
     run=[p for i,p in enumerate(run) if i==0 or math.dist(p[:2],run[i-1][:2])>1e-8]
     if len(run)<2:return
     start=run[0];previous=run[1];direction=(round(previous[0]-start[0],6),round(previous[1]-start[1],6))
     for pp in run[2:]:
      dx,dy=pp[0]-previous[0],pp[1]-previous[1]
      cross=direction[0]*dy-direction[1]*dx
      dot=direction[0]*dx+direction[1]*dy
      if abs(cross)>1e-7 or dot<0:
       addtrack(net,start[:2],previous[:2],width,layers[start[2]]);start=previous;direction=(dx,dy)
      previous=pp
     addtrack(net,start[:2],previous[:2],width,layers[start[2]])
    for pp in chain:
     if run and pp[2]!=run[-1][2]:
      flush(run);addvia(net,pp[0],pp[1]);run=[pp]
     else:run.append(pp)
    flush(run)
    route_report.append({'net':net,'from':p1['ref']+':'+p1['num'],'to':p2['ref']+':'+p2['num'],'status':'ROUTED_CANDIDATE','width_mm':width})
    success=True;break
  if not success:route_report.append({'net':net,'from':p1['ref']+':'+p1['num'],'to':p2['ref']+':'+p2['num'],'status':'UNROUTED'})
  print(net,p1['ref']+':'+p1['num'],p2['ref']+':'+p2['num'],'OK' if success else 'HOLD',flush=True)
for n in b['dsi_nets']:route_report.append({'net':n,'status':'NOT_ROUTED_CALCULATOR_HOLD','actual_copper_length_mm':0.,'end_to_end_length_mm':None})
b['route_report']=route_report;b['ground_fanout']=fan
save(b)
(ROOT/'reports/routing_status.json').write_text(json.dumps(route_report,indent=2))
print('Saved',len(b['tracks']),'segments',len(b['vias']),'vias. Unrouted edges',sum(r['status']=='UNROUTED' for r in route_report))
