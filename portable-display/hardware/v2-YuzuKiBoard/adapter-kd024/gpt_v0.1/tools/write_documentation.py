#!/usr/bin/env python3
"""Generate the two conditional cable tables and a per-reference selection list."""
from geometry import *
import csv,json
b=load();labels=json.loads((ROOT/'tools/templates/documentation.json').read_text())
j1=next(p for p in b['parts'] if p['ref']=='J1');j2=next(p for p in b['parts'] if p['ref']=='J2')
def nc(net):return net or 'NC'
text=labels['cable_intro']+'\n'
for name in ['same_face','opposite_face']:
 text+='\n## '+labels[name]+'\n\n'+labels['cable_explain']+'\n\n'
 text+=labels['cable_head']+'\n|---|---|---|---|---|---|\n'
 rows=[]
 for pin,pname,kind in b['pin_contracts']['J1']:
  if not isinstance(pin,int) or pin>24:continue
  rev=25-pin
  row=[pin,pname,pin,nc(j1['nets'].get(str(pin))),rev,nc(j1['nets'].get(str(rev)))]
  rows.append(row+['PENDING_PHYSICAL_CONTINUITY_CHECK'])
  text+='| '+' | '.join(map(str,row))+' |\n'
 with open(ROOT/'reports'/f'FFC_{name}_conditional.csv','w',newline='',encoding='utf-8-sig') as f:
  w=csv.writer(f);w.writerow(['Host_pin','Host_signal','Identity_J1_pin','Identity_board_net','Reverse_J1_pin','Reverse_board_net','Physical_mapping']);w.writerows(rows)
text+='\n'+labels['cable_warning']+'\n\n## '+labels['j1_title']+'\n\n'+labels['j1_head']+'\n|---|---|---|\n'
for pin,pname,kind in b['pin_contracts']['J1']:
 if not isinstance(pin,int) or pin>24:continue
 n=j1['nets'].get(str(pin),'')
 dest=labels['dest'].get(n,labels['nc'])
 text+=f'| {pin} | {pname} | {dest} |\n'
text+='\n## '+labels['j2_title']+'\n\n'+labels['j2_head']+'\n|---|---|---|\n'
for pin,pname,kind in b['pin_contracts']['J2']:
 if not isinstance(pin,int) or pin>45:continue
 n=j2['nets'].get(str(pin),'')
 text+=f'| {pin} | {pname} | {labels["j2_note"].get(n,n or labels["nc"])} |\n'
(ROOT/'docs/CABLE_AND_PIN_MAP.md').write_text(text)
text=labels['selection_intro']+'\n\n'+labels['selection_head']+'\n|---|---|---|---|---|\n'
for p in b['parts']:
 reason=labels['reasons'].get(p['ref'],labels['feature_reason'])
 cls=labels['not_purchased'] if p['feature'] else labels['pending_class']
 order=p['lcsc'] or labels['pending_mpn'] if not p['feature'] else '-'
 text+='| '+' | '.join([p['ref'],p['value'],reason,order,cls+(' / '+labels['dnp'] if p['dnp'] else '')])+' |\n'
text+='\n'+labels['selection_end']+'\n'
(ROOT/'docs/COMPONENT_SELECTION.md').write_text(text)
print('Two conditional 24-way cable maps, full J2 map, and 60-reference selection document written.')
