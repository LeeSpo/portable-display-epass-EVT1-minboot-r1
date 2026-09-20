from last_signals import *
from fanout import force
shutil.copy2(P,W/'24_before_finish.kicad_pcb')
b=rb.load(P);its=rb.board_items(b);rem=set()
for i in its:
 if i.kind=='via' and i.net=='3V3' and math.dist(i.pos,(23.55,31.075))<.02:rem.add(i.label)
 if i.kind=='track' and 'F.Cu' in i.layers and i.net=='3V3' and any(math.dist(p,(23.55,31.075))<.02 or math.dist(p,(23.55,30.85))<.02 for p in i.pos):rem.add(i.label)
 if i.kind=='track' and 'F.Cu' in i.layers and i.net=='LCD_RST' and all(22<=x<=24.1 and 31.2<=y<=32.8 for x,y in i.pos):rem.add(i.label)
save(cut(b,rem))
force('LCD_RST',[(22.4,31.325),(22.95,31.325),(22.95,32.0),(23.1,32.15),(23.55,32.15),(24,32.6),(24,32.7)],via=False)
force('LCD_TE',[(22.4,30.975),(23.1,30.975),(23.425,31.3),(23.6,31.3)])
prune();run(['LCD_TE','LCD_RST','SD_PWR_GATE','3V3'],.025)
status()
