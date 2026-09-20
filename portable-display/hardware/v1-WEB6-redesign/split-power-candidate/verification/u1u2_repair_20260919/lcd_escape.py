from last_signals import *
from fanout import force
shutil.copy2(P,W/'22_before_lcd_escape.kicad_pcb')
b=rb.load(P);its=rb.board_items(b);rem=set()
for i in its:
 if i.kind=='via' and i.net in ('3V3','LCD_TE') and (math.dist(i.pos,(23.3,30.7))<.02 or math.dist(i.pos,(23.65,31.8))<.02):rem.add(i.label)
 if i.kind=='track' and 'F.Cu' in i.layers and i.net in ('3V3','LCD_TE') and all(22<=x<=24.1 and 30.1<=y<=31.9 for x,y in i.pos):rem.add(i.label)
save(cut(b,rem))
force('3V3',[(22.4,30.275),(22.875,30.275),(23.275,30.675),(23.725,30.675),(24.15,31.1),(24.3,31.1)],.18)
force('LCD_TE',[(22.4,30.975),(23.1,30.975),(23.625,31.5),(24.025,31.9),(24.3,31.9)])
force('LCD_RST',[(22.4,31.325),(22.6,31.335),(23.1,31.335),(23.625,31.86),(24.,32.235),(24.,32.7)])
prune();run(['3V3','LCD_TE','LCD_RST'],.025)
shutil.copy2(P,W/'23_lcd_escape.kicad_pcb')
