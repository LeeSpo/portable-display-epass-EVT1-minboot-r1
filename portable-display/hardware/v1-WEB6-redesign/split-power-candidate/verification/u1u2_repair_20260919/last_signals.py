from negotiate import *
def obstacles(self,net,width,layer):return VerifiedRouter._obstacles(self,net,width,layer).buffer(.0005)
def check(self,g,layers,net,hole=None):return VerifiedRouter._ok(self,g,layers,net,hole)
RepairRouter._obstacles=obstacles;RepairRouter._ok=check
if __name__=='__main__':
 shutil.copy2(P,W/'18_before_bridge_merge.kicad_pcb');shutil.copy2(W/'bridges.kicad_pcb',P)
 batch(['UART0_RX','PMIC_IRQ_N','LCD_TE'],CRITICAL|{'CORE_0V93','DRAM_1V5','1V8','3V3','VSYS','VBUS','VBAT'},.025)
 prune();shutil.copy2(P,W/'19_three_signals.kicad_pcb')
 r=RepairRouter(rb.load(P));names=[n for n in sorted(set(i.net for i in r.items)) if not rb.skip_net(n) and len(r.groups(n))>1];print('victims',names,flush=True);run(names)
