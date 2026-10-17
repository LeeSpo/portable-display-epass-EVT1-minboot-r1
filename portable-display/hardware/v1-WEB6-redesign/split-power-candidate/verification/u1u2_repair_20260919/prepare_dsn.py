from repair import *
import re
s=(W/'finish.dsn').read_text()
# Netclass line widths govern only new routing; preserve existing copper widths.
s=s.replace('(width 200)','(width 127)').replace('(clearance 31.75 (type smd_smd))','(clearance 127 (type smd_smd))')
# KiCad's object-specific allow-track rule areas should not become solid trace
# keepouts on export; retain them as-is in this conservative trial.
locked=CRITICAL|{'EL_SWP','EL_SWN'}
lines=[]
for line in s.splitlines():
 m=re.search(r'\(net ([^()]*)\)\(type route\)',line)
 if m and m[1].strip('"') in locked:line=line.replace('(type route)','(type protect)')
 lines.append(line)
(W/'finish_protected.dsn').write_text('\n'.join(lines)+'\n')
shutil.copy2(P,W/'17_before_freerouting.kicad_pcb')
