from last_signals import *
from fanout import force
b=rb.load(P);its=rb.board_items(b)
rem={i.label for i in its if i.net=='3V3' and i.kind=='track' and 'F.Cu' in i.layers and all(13.69<=x<=13.91 and 20.59<=y<=22.26 for x,y in i.pos)}
b=cut(b,rem);r=RepairRouter(b)
assert r.commit_xy([(13.9,20.6,'F.Cu'),(13.7,20.8,'F.Cu'),(13.7,21.95,'F.Cu')],.18,'3V3')
save(b);r.write();print('3V3 channel moved',len(rem),flush=True)
force('LCD_RST',[(22.4,31.325),(21.95,31.325),(21.725,31.55),(21.6,31.55)])
run(['UART0_TX','LCD_RST'],.025)
batch(['PMIC_SDA'],CRITICAL|{'CORE_0V93','DRAM_1V5','1V8','3V3','VSYS','VBAT','PMIC_IRQ_N','PMIC_SCL'},.025)
prune();shutil.copy2(P,W/'21_targeted_channels.kicad_pcb')
r=RepairRouter(rb.load(P));names=[n for n in sorted(set(i.net for i in r.items)) if not rb.skip_net(n) and len(r.groups(n))>1];print('remaining',names,flush=True);run(names,.025,.127)
