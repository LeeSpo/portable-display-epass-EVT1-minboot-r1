import repair as rp
from repair import *
alt=W/'bridges.kicad_pcb'
if not alt.exists():shutil.copy2(P,alt);shutil.copy2(P.with_suffix('.kicad_pro'),alt.with_suffix('.kicad_pro'))
rp.P=alt;rb.BOARD=alt
# Existing In2 is explicitly a split-power + local-signal bridge layer.
# Model zone clearance by native refill, instead of forbidding all such bridges.
# In1 is excluded from routing. Check lengths and native DRC after this trial.
def obstacles(self,net,width,layer):return VerifiedRouter._obstacles(self,net,width,layer).buffer(.0005)
def check(self,g,layers,net,hole=None):return VerifiedRouter._ok(self,g,layers,net,hole)
RepairRouter._obstacles=obstacles;RepairRouter._ok=check
r=RepairRouter(rb.load(alt));nets=[n for n in sorted(set(i.net for i in r.items)) if not rb.skip_net(n) and len(r.groups(n))>1]
print('remaining',nets,flush=True);rp.run(nets)
r=RepairRouter(rb.load(alt));nets=[n for n in nets if len(r.groups(n))>1]
if nets:rp.run(nets,.025,.127)
