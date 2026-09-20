from repair import *
def force(net,points,width=.127,via=True):
 b=rb.load(P);its=rb.board_items(b);rem=set();blocked=[]
 checks=[(LineString([a,b]).buffer(width/2),{'F.Cu'},None) for a,b in zip(points,points[1:])]
 if via:checks.append((Point(points[-1]).buffer(.3),{'F.Cu','B.Cu','In1.Cu','In2.Cu'},Point(points[-1]).buffer(.15)))
 for g,ls,h in checks:
  for i in its:
   same=i.net==net;bad=not same and bool(i.layers&ls) and g.distance(i.geom)<.127-1e-6
   bad|=h is not None and i.hole is not None and h.distance(i.hole)<.25-1e-6
   bad|=not same and h is not None and bool(i.layers) and h.distance(i.geom)<.25-1e-6
   bad|=not same and i.hole is not None and i.hole.distance(g)<.25-1e-6
   if not bad:continue
   if i.kind not in ('track','via') or i.net in CRITICAL:blocked.append((i.label,i.net))
   else:rem.add(i.label)
 if blocked:print('BLOCKED',net,blocked,flush=True);return False
 b=cut(b,rem);r=RepairRouter(b);pts=[(*p,'F.Cu') for p in points]
 if via:pts.append((*points[-1],'B.Cu'))
 if len(points)==1:ok=r.add_via(*points[0],net)
 else:ok=r.commit_xy(pts,width,net)
 if not ok:print('FAIL',net,flush=True);return False
 save(b);r.write();print('fanout',net,'removed',len(rem),sorted(set(i.net for i in its if i.label in rem)),flush=True);return True
if __name__=='__main__':
 force('SOC_LDO_1V8',[(22.4,27.125),(22.975,27.125),(23.35,27.5)])
 force('CORE_0V93',[(22.4,27.475),(21.68,27.435)],.18)
 force('SD_CMD',[(22.4,28.875),(21.68,28.915)])
 force('SD_D2',[(22.4,28.175),(21.68,28.175)])
 force('SD_DET',[(22.4,27.825),(22.875,27.825),(23.35,28.3)])
 # Replace SD_CLK local segment only if necessary after other escapes.
 force('SD_D3',[(22.4,28.525),(22.78,28.525),(23.055,28.8),(23.6,28.8),(23.825,29.025),(25.095,29.025),(25.4,28.72)])
 force('SD_D0',[(22.4,29.575),(23.0,29.575),(23.35,29.925)])
 force('SD_D0',[(24.3,27.5)])
 force('SD_D1',[(22.4,29.925),(22.0,29.925),(21.7,29.9)])
 force('3V3',[(22.4,30.275),(22.875,30.275),(23.3,30.7)],.18)
 force('PMIC_SDA',[(16.425,23.6),(16.425,24.32)])
 force('DRAM_1V5',[(17.125,23.6),(17.19,24.32)],.18)
 force('PMIC_SDA',[(26.4,52.9),(26.4,53.6)])
 prune();shutil.copy2(P,W/'03_fanouts.kicad_pcb')
