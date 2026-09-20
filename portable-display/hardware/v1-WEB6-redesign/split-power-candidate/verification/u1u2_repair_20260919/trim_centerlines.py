from last_signals import *
from fanout import force
shutil.copy2(P,W/'34_before_centerline_trim.kicad_pcb')
force('3V3',[(24.3,31.1),(24.675,31.1),(24.85,31.275)],.18,False)
b=rb.load(P);save(cut(b,{'015ade89-8922-589e-a1af-9f10e2fa68c4'}))
b=rb.load(P);its=rb.board_items(b)+zones(b);rem=set()
for net in ['CORE_0V93','CHGLED_N']:
 ns=[i for i in its if i.net==net];geoms={i.label:LineString(i.pos) if i.kind=='track' else i.geom for i in ns}
 for _ in range(2000):
  live=[i for i in ns if i.label not in rem];tree=STRtree([geoms[i.label] for i in live]);new=set()
  for i in live:
   if i.kind!='track':continue
   for p in i.pos:
    pt=Point(p);radius=float(val(i.node,'width'))/2
    if not any(live[int(j)] is not i and live[int(j)].layers&i.layers and geoms[live[int(j)].label].distance(pt)<(1e-5 if live[int(j)].kind=='track' else radius+1e-6) for j in tree.query(pt.buffer(radius+1e-6))):new.add(i.label);break
  if not new:break
  rem.update(new)
save(cut(b,rem));print('Centerline dead-branch removal',len(rem),flush=True);status()
