from last_signals import *
from fanout import force
shutil.copy2(P,W/'25_before_pmic_escape.kicad_pcb')
b=rb.load(P)
f=next(f for f in children(b,'footprint') if any(p[1]=='Reference' and p[2]=='C38' for p in children(f,'property')))
a=list(values(f,'at'));a[1]=str(float(a[1])+.4);setval(f,'at',*a)
its=rb.board_items(b);rem=set()
for i in its:
 if i.net in ('PMIC_IRQ_N','PMIC_SCL','PMIC_SDA'):
  if i.kind=='via' and 25.8<i.pos[0]<27.7 and 53.3<i.pos[1]<54:rem.add(i.label)
  if i.kind=='track' and 'F.Cu' in i.layers and all(25.8<x<27.7 and 52.7<y<54 for x,y in i.pos):rem.add(i.label)
 if i.net=='VBUS' and i.kind=='track' and 'F.Cu' in i.layers and all(25.4<x<26.65 and 52.7<y<54.5 for x,y in i.pos):rem.add(i.label)
byid={i.label:i for i in its}
for v in issues(its,clearance=.127):
 if not any(v[k].startswith('C38.') for k in ['a','b']):continue
 for k in ['a','b']:
  i=byid.get(v[k])
  if i and i.kind in ('track','via'):
   if i.net in CRITICAL:raise RuntimeError('critical conflict')
   rem.add(i.label)
print('remove',len(rem),sorted(set(i.net for i in its if i.label in rem)),flush=True)
save(cut(b,rem))
force('VBUS',[(25.6,52.9),(25.6,53.15),(25.525,53.225),(25.525,53.975),(25.825,54.275),(26.425,54.275),(26.6,54.45)],.18,False)
force('PMIC_IRQ_N',[(26,52.9),(26,53.2),(26.05,53.25),(26.05,53.63)])
force('PMIC_SDA',[(26.4,52.9),(26.425,53.225),(26.85,53.65)])
force('PMIC_SCL',[(26.8,52.9),(27.05,52.9),(27.6,53.45),(27.6,53.65)])
prune();run(['PMIC_IRQ_N','PMIC_SDA','PMIC_SCL','VBUS','VMID','VSYS','CHGLED_N'],.025)
status();shutil.copy2(P,W/'26_pmic_escape.kicad_pcb')
