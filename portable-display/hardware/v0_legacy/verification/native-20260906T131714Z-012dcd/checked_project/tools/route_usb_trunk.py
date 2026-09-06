#!/usr/bin/env python3
"""Generate a coupled USB trunk candidate; stackup/impedance signoff is separate."""
import sys,copy,math
from pathlib import Path
from shapely.geometry import LineString,Point
from complete_minboot import Closure,Item,load,dump,children,val,values,Router
from kicad_sexpr import Q
from geometry_audit import board_items,issues

def main():
 src=Path(sys.argv[1]);out=Path(sys.argv[2]);b=load(src)
 # Replace only the long SoC-to-ESD trunks. Keep connector/ESD local wiring and SoC pad escapes.
 items=board_items(b);remove=set()
 for i in items:
  if i.net not in ('USB_DP','USB_DM'):continue
  if i.kind=='track':
   if max(p[1] for p in i.pos)>94 and min(p[1] for p in i.pos)>94:
    # Old DP bottom horizontal and end stub are part of the trunk.
    if i.net=='USB_DP' and 'B.Cu' in i.layers:remove.add(id(i.node))
    continue
   if 'F.Cu' in i.layers and all(30.0<=p[0]<=31 and 48<=p[1]<=51.3 for p in i.pos):continue
   remove.add(id(i.node))
  elif i.kind=='via' and 46<i.pos[1]<96 and not any(math.dist(i.pos,p)<.001 for p in [(30.8663,48.1625),(30.2888,48.1625),(28.05,95.4),(29.95,95.4)]):remove.add(id(i.node))
 b[:]=[x for x in b if id(x) not in remove]
 r=Closure(copy.deepcopy(b),[]);r.ids['USB_PAIR']=999
 # Work only on B.Cu: keep all transitions at the existing endpoint fanouts.
 r.obstacles('USB_PAIR',.4);r.block[0,:,:]=True
 a=Item('pad','USB_PAIR',frozenset(('B.Cu',)),Point(30.5775,46.95).buffer(.01),[],'start',pos=(30.5775,46.95))
 z=Item('pad','USB_PAIR',frozenset(('B.Cu',)),Point(29,94).buffer(.01),[],'end',pos=(29,94))
 if not r.join('USB_PAIR',[a],[z],.4):raise RuntimeError('No single-layer shared corridor')
 segs=[x for x in r.items if x.net=='USB_PAIR'];pts=[segs[0].pos[0]]+[x.pos[1] for x in segs]
 center=LineString(pts)
 for sign in (1,-1):
  candidate=copy.deepcopy(b);rr=Router(candidate);ok=True;ends=[]
  for net,distance,start,end in [('USB_DP',sign*.135,(30.8663,48.1625),(28.05,95.4)),('USB_DM',-sign*.135,(30.2888,48.1625),(29.95,95.4))]:
   line=center.offset_curve(distance,join_style=2);coords=list(line.coords)
   pieces=[('seg',(*a,*z,.09,'B.Cu',net,f'usb-coupled-{net}-{j}')) for j,(a,z) in enumerate(zip(coords,coords[1:]))]
   if not rr.commit(pieces):
    print('offset fail',sign,net,flush=True);ok=False;break
   ends.append((net,start,end,coords))
  if not ok:continue
  for net,start,end,coords in ends:
   if not rr._manhattan(*start,*coords[0],'B.Cu',.09,net,'usb-entry-'+net):
    print('entry fail',sign,net,start,coords[0],flush=True);ok=False;break
   if not rr._manhattan(*end,*coords[-1],'B.Cu',.09,net,'usb-exit-'+net):
    print('exit fail',sign,net,end,coords[-1],flush=True);ok=False;break
  if ok and not issues(board_items(candidate)):
   rr._strip_zone_fills();dump(candidate,out);print('coupled trunk',center.length,'mm; center spacing 0.27 mm',flush=True);return
 raise RuntimeError('Offset pair or endpoint escapes collide; source unchanged')
if __name__=='__main__':main()
