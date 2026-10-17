#!/usr/bin/env python3
"""Deterministic engineering candidate, not a fabrication-release generator.
Only stdlib + shapely/numpy/scipy/reportlab/cairosvg for auxiliary tools.
DSI copper is deliberately absent until the specified calculator is verified.
"""
from __future__ import annotations
import json, math, uuid, pathlib, csv, hashlib, re, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
K=ROOT/'kicad'
NS=uuid.UUID('e10b7820-c443-4dbe-85f3-85ecbf0d4a44')
def uid(s):return str(uuid.uuid5(NS,s))
def q(s): return json.dumps(str(s),ensure_ascii=False)
def f(x):return f'{float(x):.6f}'.rstrip('0').rstrip('.') or '0'
B={'name':'adapter_v0.1','revision':'0.1-review.1','fabrication_released':False,
   'board':[50.,44.,92.,82.],'thickness_mm':1.0,'target_stackup':'JLC04101H-3313',
   'stackup_verified':False,'aux_origin':[50.,82.],'parts':[],'nets':[],
   'tracks':[],'vias':[],'footprints':{},'holes':[],
   'dsi_nets':['DSI_D0_P','DSI_D0_N','DSI_CK_P','DSI_CK_N']}
F=B['footprints']; parts=B['parts']; P={}
def pad(num,x,y,w,h,shape='rect',kind='smd',drill=None,layers=None,paste=True,mask=True):
 return dict(num=str(num),x=x,y=y,w=w,h=h,shape=shape,kind=kind,drill=drill,
             layers=layers or (['*.Cu','*.Mask'] if kind=='thru_hole' else ['F.Cu']+(['F.Paste'] if paste else [])+(['F.Mask'] if mask else [])))
def fp(name,pads,body,source,height=1.0,open_side=None,paste_windows=None):
 F[name]={'pads':pads,'body':body,'source':source,'height':None if name.startswith(('R_','C_','Header_')) else height,'open_side':open_side,
          'paste_windows':paste_windows or []}
# All dimensions are mm. J1 signal numbering descends left-to-right in top view.
fp('Hirose_FH34SRJ_24S_0.5SH_50',
 [pad(i,5.75-.5*(i-1),-1.25,.30,.80,paste=False) for i in range(1,25)]+
 [pad('MP1',-6.75,1.25,.4,.8),pad('MP2',6.75,1.25,.4,.8)],
 [-7.,-1.65,7.,2.15], 'Hirose EDC-159714-50-08, recommended PCB p1; 24-way dimensions p4',1.,'+Y',
 [(5.75-.5*i,-1.25,.25,.65) for i in range(24)])
fp('Molex_502598_4593_45P_Staggered',
 [pad(i,-6.6+.3*(i-1),0 if i%2 else -3.065,.3,.67 if i%2 else .5) for i in range(1,46)]+
 [pad('MP1',-7.4,-.265,.35,1.),pad('MP2',7.4,-.265,.35,1.)],
 [-7.8,-3.365,7.8,.435], 'Molex SD-502598-003 Rev A sheets 1-2; pin-1 mating orientation requires physical signoff',1.15,'+Y')
fp('TI_TPS65631_DPD_12_EP',
 [pad(i,-1.45,-1.125+.45*(i-1),.70,.25) for i in range(1,7)]+
 [pad(i,1.45,-1.125+.45*(12-i),.70,.25) for i in range(7,13)]+
 [pad(13,0,0,1.21,2.02,paste=False)],[-1.5,-1.5,1.5,1.5],
 'TI TPS65631 DPD drawing, local PDF pages 22-24; peripheral lands engineering-derived; stencil review open',.8,None,
 [(0,-.5,.95,.75),(0,.5,.95,.75)])
fp('TI_TLV767_DRV_6_EP',
 [pad(i,-.975,-.65+.65*(i-1),.45,.30) for i in range(1,4)]+
 [pad(i,.975,-.65+.65*(6-i),.45,.30) for i in range(4,7)]+
 [pad(7,0,0,1.,1.6,paste=False)],[-1.,-1.,1.,1.],
 'TI TLV767 DRV0006A 4222173/C 11-2025, EXAMPLE BOARD LAYOUT; no vias in exposed pad',.8,None,
 [(0,-.45,1.,.7),(0,.45,1.,.7)])
fp('TI_DBV_SOT23_5',
 [pad(1,-1.3,-.95,1.1,.6),pad(2,-1.3,0,1.1,.6),pad(3,-1.3,.95,1.1,.6),pad(4,1.3,.95,1.1,.6),pad(5,1.3,-.95,1.1,.6)],
 [-.8,-1.45,.8,1.45], 'TI DBV0005A recommended PCB, 2.6 mm opposing pad-centre spacing / 0.95 mm pitch',1.45)
fp('Coilcraft_XFL4020_472MEC', [pad(1,-1.185,0,.98,3.4),pad(2,1.185,0,.98,3.4)],
 [-2.15,-2.15,2.15,2.15], 'Coilcraft XFL4020 official dimensional drawing, Document 1149; lands 0.98 x 3.4, centres 2.37',2.1)
for n,w,h,x,bw,bh in [('R_0603',.9,1.0,.85,1.6,.8),('C_0603',.9,1.0,.85,1.6,.8),('C_0805',1.15,1.45,1.,2.0,1.25)]:
 fp(n,[pad(1,-x,0,w,h),pad(2,x,0,w,h)],[-bw/2,-bh/2,bw/2,bh/2],
    'Project engineering land pattern for nominal metric chip body; exact purchased MPN must be checked',.9 if n=='C_0805' else .8)
for n in [13,5]:
 fp(f'Header_1x{n:02d}_P2.54_PassThrough', [pad(i,-2.54*(i-1),0,1.7,1.7,'rect' if i==1 else 'circle','thru_hole',1.0) for i in range(1,n+1)],
 [-(n-1)*2.54-1.27,-1.27,1.27,1.27], 'XY extracted from original Gerber drill; hole/pad overridden to requested 1.0 / 1.7 mm; bottom mating manual fit',2.5)
fp('Mount_M2_NPTH_2.2', [pad('',0,0,2.2,2.2,'circle','np_thru_hole',2.2,['*.Cu','*.Mask'],False)],
 [-1.1,-1.1,1.1,1.1], 'M2 NPTH 2.2; 1.5 mm radial component/copper keepout (r=2.6)',0.)
fp('Fiducial_1mm_Mask2mm',[pad('',0,0,1.,1.,'circle',paste=False,mask=False)],[-.5,-.5,.5,.5],
 'Task: 1.0 mm copper, 2.0 mm mask opening',0.)
fp('TestPoint_1.2mm',[pad(1,0,0,1.2,1.2,'circle',paste=False)],[-.6,-.6,.6,.6], 'Bare copper probe pad; no assembly component',0.)
# Pin data is an independent schematic contract, not inferred from footprint numbers.
pins={
 'TPS65631':[(1,'SWP','passive'),(2,'PGND','power_in'),(3,'OUTP','power_out'),(4,'FBS','input'),(5,'AGND','power_in'),(6,'GND','power_in'),(7,'CTRL','input'),(8,'CT','passive'),(9,'OUTN','power_out'),(10,'SWN','passive'),(11,'AVIN','power_in'),(12,'PVIN','power_in'),(13,'EP','power_in')],
 'TLV76701DRVR':[(1,'OUT','power_out'),(2,'FB','input'),(3,'GND','power_in'),(4,'EN','input'),(5,'GND','power_in'),(6,'IN','power_in'),(7,'EP','power_in')],
 'TLV75518PDBVR':[(1,'IN','power_in'),(2,'GND','power_in'),(3,'EN','input'),(4,'NC','no_connect'),(5,'OUT','power_out')],
 'SN74LVC1G17DBVR':[(1,'NC','no_connect'),(2,'A','input'),(3,'GND','power_in'),(4,'Y','output'),(5,'VCC','power_in')],
 'R':[(1,'1','passive'),(2,'2','passive')], 'C':[(1,'1','passive'),(2,'2','passive')],
 'L':[(1,'1','passive'),(2,'2','passive')], 'TP':[(1,'1','passive')], 'Mechanical':[],
 'PWR_FLAG':[(1,'pwr','power_out')]}
j1names=['GND','D0N','D0P','GND','CKN','CKP','GND','D1N_NC','D1P_NC','GND','3V3','3V3','GND','3V3','GND','NC','GND','DSI_RST_3V3','GND','NC','NC','LEDK_NC','GND','LEDA_HV_NC']
j1net={str(i):'GND' for i in [1,4,7,10,13,15,17,19,23]}
j1net.update({'2':'DSI_D0_N','3':'DSI_D0_P','5':'DSI_CK_N','6':'DSI_CK_P','11':'HOST_3V3_LOGIC','12':'HOST_3V3_LOGIC','14':'HOST_3V3_LOGIC','18':'HOST_RST_3V3','MP1':'GND','MP2':'GND'})
j2names={1:'GND',2:'GND',3:'ELVSS',4:'ELVSS',5:'GND',6:'ELVDD',7:'ELVDD',8:'GND',9:'VCI',10:'GND',11:'VDDIO',12:'GND',13:'TE1',14:'SWIRE_OUT',15:'TE',16:'RESX',17:'GND',18:'SDI_RDX',19:'DCX',20:'SCL',21:'CSX',22:'D0',23:'D1',24:'D2',25:'D3',26:'D4',27:'D5',28:'D6',29:'D7',30:'GND',31:'IM1',32:'IM0',33:'GND',34:'GND',35:'D0P',36:'D0N',37:'GND',38:'GND',39:'CLKP',40:'CLKN',41:'GND',42:'GND',43:'MTP',44:'GND',45:'GND'}
j2net={str(i):'GND' for i,n in j2names.items() if n=='GND'}
j2net.update({str(i):n for i,n in {3:'ELVSS',4:'ELVSS',6:'ELVDD',7:'ELVDD',9:'PANEL_VCI_3V3',11:'VDDIO_1V8',13:'PANEL_TE1',14:'PANEL_SWIRE',15:'PANEL_TE',16:'PANEL_RESET_1V8',31:'GND',32:'GND',35:'DSI_D0_P',36:'DSI_D0_N',39:'DSI_CK_P',40:'DSI_CK_N',43:'GND'}.items()})
j2net.update({'MP1':'GND','MP2':'GND'})
pins['J1']=[(i,n,'passive') for i,n in enumerate(j1names,1)]+[('MP1','MP1','passive'),('MP2','MP2','passive')]
pins['J2']=[(i,n,'passive') for i,n in j2names.items()]+[('MP1','MP1','passive'),('MP2','MP2','passive')]
for n in [13,5]:pins[f'H{n}']=[(i,('VBUS_5V' if n==13 and i==13 else '3V3' if n==5 and i==3 else 'GND' if (n==13 and i in [1,12]) or (n==5 and i==1) else 'UNUSED'), 'passive') for i in range(1,n+1)]

def add(ref,value,foot,x,y,nets,sym,section='root',angle=0,dnp=False,feature=False,lcsc='',mpn='',reason=''):
 o={'ref':ref,'value':value,'footprint':foot,'x':x,'y':y,'angle':angle,'nets':{str(k):v for k,v in nets.items()},'symbol':sym,
    'section':section,'dnp':dnp,'feature':feature,'lcsc':lcsc,'mpn':mpn or value,'reason':reason,
    'uuid':uid('symbol:'+ref),'footprint_uuid':uid('footprint:'+ref),'library_class':'PENDING_CONFIRMATION'}
 parts.append(o);P[ref]=o;return o
add('J1','FH34SRJ-24S-0.5SH(50)','Hirose_FH34SRJ_24S_0.5SH_50',65.3022,79.2,j1net,'J1',reason='24P host FFC; electrical numbering assumes verified identity harness; cable orientation not signed off')
add('J2','502598-4593','Molex_502598_4593_45P_Staggered',76.5,45.4,j2net,'J2',angle=180,lcsc='C5365339',reason='45P staggered lands; replaces panel-referenced -4591 only after physical approval')
add('H1','MANUAL: 1x13 pass-through','Header_1x13_P2.54_PassThrough',87.197,55.127,{'1':'GND','12':'GND','13':'VBUS_5V'},'H13',dnp=True,reason='Bottom mating to host, manual fit; exact Gerber XY; all other pads no electrical net')
add('H2','MANUAL: 1x05 pass-through','Header_1x05_P2.54_PassThrough',87.197,75.040,{'1':'GND','3':'PANEL_VCI_3V3'},'H5',dnp=True,reason='Bottom mating to host, manual fit; do not bridge with J1 logic 3V3 on adapter')
add('U1','TPS65631DPDR','TI_TPS65631_DPD_12_EP',59.5,64.2,{1:'SWP',2:'GND',3:'ELVDD',4:'ELVDD_SENSE',5:'GND',6:'GND',7:'LCD_EN',8:'BIAS_CT',9:'ELVSS',10:'SWN',11:'BIAS_IN_3V6',12:'BIAS_IN_3V6',13:'GND'},'TPS65631','bias',reason='Required chip; 2.9-4.5 V operating input; defaults +4.6 / -4.0 V are not panel-approved')
add('U2','TLV76701DRVR','TI_TLV767_DRV_6_EP',55.8,72.,{1:'PRE_3V584',2:'LDO_FB',3:'GND',4:'VBUS_5V',5:'GND',6:'VBUS_5V',7:'GND'},'TLV76701DRVR','bias',reason='16 V input rating, adjustable 0.8 V feedback, preregulates 5 V to 3.584 V; thermal review required')
add('U3','TLV75518PDBVR','TI_DBV_SOT23_5',80.5,61.5,{1:'LOGIC_LDO_IN',2:'GND',3:'LOGIC_LDO_IN',5:'VDDIO_1V8'},'TLV75518PDBVR','logic',reason='Fixed 1.8 V logic LDO supplied only from J1 11/12/14; enabled with input')
add('U4','SN74LVC1G17DBVR','TI_DBV_SOT23_5',80.5,68.8,{2:'HOST_RST_3V3',3:'GND',4:'PANEL_RESET_1V8',5:'VDDIO_1V8'},'SN74LVC1G17DBVR','logic',reason='Non-inverting Schmitt buffer at 1.8 V, accepts 3.3 V input and has Ioff; no direct 3.3 V RESX drive')
add('L1','4.7uH XFL4020-472MEC','Coilcraft_XFL4020_472MEC',55.3,61.,{1:'BIAS_IN_3V6',2:'SWP'},'L','bias',mpn='XFL4020-472MEC',reason='4.7 uH +/-20%, DCR max 57.4 mOhm; saturation and temperature margins must be confirmed')
add('L2','4.7uH XFL4020-472MEC','Coilcraft_XFL4020_472MEC',63.4,69.1,{1:'SWN',2:'GND'},'L','bias',angle=270,mpn='XFL4020-472MEC',reason='Inverting topology: L2 goes from SWN to GND, NOT to VIN; same current-qualified candidate as L1')
R=[('R1','0R 0603',62.4,73.9,'PRE_3V584','BIAS_IN_3V6','bias'),('R2','0R 0603',76.2,63.2,'HOST_3V3_LOGIC','LOGIC_LDO_IN','logic'),('R3','34.8k 1%',53.5,75.2,'PRE_3V584','LDO_FB','bias'),('R4','10k 1%',56.5,75.2,'LDO_FB','GND','bias'),('R5','10k 1%',59.,69.3,'LCD_EN','GND','bias'),('R6','100k 1%',76.8,69.8,'HOST_RST_3V3','GND','logic'),('R7','100k 1%',84.7,70.3,'PANEL_RESET_1V8','GND','logic'),('R8','0R DNP',85.2,65.2,'PANEL_SWIRE','LCD_EN','logic')]
for r,val,x,y,a,b,s in R:add(r,val,'R_0603',x,y,{1:a,2:b},'R',s,dnp=r=='R8',mpn='PROCUREMENT_PENDING',reason={'R1':'Removable 0603 input current link for TPS65631','R2':'Removable 0603 input current link for 1.8 V LDO','R3':'Top feedback resistor, 0.8*(1+34.8/10)=3.584 V','R4':'Bottom feedback resistor','R5':'Required 10k enable pull-down; bias defaults OFF','R6':'Default host-reset low without FFC','R7':'Default panel reset low; 18 uA load at 1.8 V','R8':'DO NOT FIT: optional SWIRE-to-CTRL link pending output direction/timing review'}[r])
add('R9','0R 0603 Kelvin','R_0603',55.3,67.35,{1:'ELVDD_SENSE',2:'ELVDD'},'R','bias',mpn='PROCUREMENT_PENDING',reason='Kelvin sense isolation link: place star at C9 positive; route ELVDD_SENSE independently to FBS')
C=[('C1',10,58.5,73.6,'VBUS_5V',0),('C2',.1,58.7,71.6,'VBUS_5V',0),('C3',10,52.4,72.,'PRE_3V584',180),('C4',.1,53.,69.5,'PRE_3V584',180),('C5',10,62.8,59.9,'BIAS_IN_3V6',90),('C6',10,65.5,60.,'BIAS_IN_3V6',90),('C7',.1,63.3,62.8,'BIAS_IN_3V6',0),('C8',.1,66.2,62.8,'BIAS_IN_3V6',0),('C9',10,55.3,65.2,'ELVDD',180),('C10',10,63.2,65.,'ELVSS',0),('C11',10,66.6,65.,'ELVSS',0),('C12',.1,58.9,67.15,'BIAS_CT',0),('C13',4.7,76.2,60.6,'LOGIC_LDO_IN',0),('C14',.1,79.2,58.9,'LOGIC_LDO_IN',0),('C15',4.7,84.7,60.6,'VDDIO_1V8',0),('C16',.1,84.7,62.8,'VDDIO_1V8',0),('C17',.1,84.7,67.8,'VDDIO_1V8',0),('C18',1.,79.,50.5,'PANEL_VCI_3V3',90),('C19',.1,81.,50.5,'PANEL_VCI_3V3',90),('C20',1.,75.,50.5,'VDDIO_1V8',90),('C21',.1,77.,50.5,'VDDIO_1V8',90),('C22',1.,83.,50.5,'ELVDD',90),('C23',1.,85.,50.5,'ELVSS',90)]
for r,val,x,y,net,ang in C:
 sec='bias' if int(r[1:])<=12 else 'logic' if int(r[1:])<=17 else 'root'
 add(r,('%guF 10V X7R'%val),'C_0805' if val==10 else 'C_0603',x,y,{1:net,2:'GND'},'C',sec,angle=ang,mpn='PROCUREMENT_PENDING',reason='10 V minimum MLCC; verify effective capacitance versus DC bias, temperature and selected MPN')
TP=[('TP1',52.,68.,'VBUS_5V','bias'),('TP2',65.8,73.4,'BIAS_IN_3V6','bias'),('TP3',52.,64.,'ELVDD','bias'),('TP4',67.4,67.4,'ELVSS','bias'),('TP5',87.8,63.8,'VDDIO_1V8','logic'),('TP6',87.8,67.4,'PANEL_VCI_3V3','logic'),('TP7',65.,75.,'LCD_EN','bias'),('TP8',87.8,58.8,'PANEL_TE1','logic'),('TP9',87.8,61.2,'PANEL_TE','logic'),('TP10',83.,65.2,'PANEL_SWIRE','logic'),('TP11',87.8,70.2,'PANEL_RESET_1V8','logic'),('TP12',74.3,69.4,'GND','logic')]
for r,x,y,n,s in TP:add(r,n,'TestPoint_1.2mm',x,y,{1:n},'TP',s,feature=True,reason='Copper test point; excluded from assembly BOM/CPL, listed separately')
for i,(x,y) in enumerate([(52.75,46.75),(89.25,46.75),(52.75,79.25),(89.25,79.25)],1):
 add(f'MH{i}','M2 NPTH 2.2','Mount_M2_NPTH_2.2',x,y,{},'Mechanical',feature=True);B['holes'].append([x,y,1.1,2.6])
for i,(x,y) in enumerate([(56.7,46.4),(85.6,79.7)],1):add(f'FID{i}','FID 1mm / 2mm mask','Fiducial_1mm_Mask2mm',x,y,{},'Mechanical',feature=True)
# Put SMT connector anchors at their nominal body centres, so native CPL
# positions do not silently use the odd contact row as the placement centroid.
for name in ['Hirose_FH34SRJ_24S_0.5SH_50','Molex_502598_4593_45P_Staggered']:
 d=F[name];cx=(d['body'][0]+d['body'][2])/2;cy=(d['body'][1]+d['body'][3])/2
 for pp in parts:
  if pp['footprint']==name:
   a=math.radians(pp['angle']);pp['x']+=cx*math.cos(a)+cy*math.sin(a);pp['y']+=-cx*math.sin(a)+cy*math.cos(a)
 for aa in d['pads']:aa['x']-=cx;aa['y']-=cy
 d['body']=[d['body'][0]-cx,d['body'][1]-cy,d['body'][2]-cx,d['body'][3]-cy]
 d['paste_windows']=[(x-cx,y-cy,w,h) for x,y,w,h in d['paste_windows']]
 d['origin_note']='Nominal body centre; manufacturer pickup position still requires assembly preview approval'
B['nets']=sorted({n for p in parts for n in p['nets'].values()})
B['pin_contracts']=pins
# Pin-level physical coordinates.
def transform(p,x,y):
 a=math.radians(p['angle']);return p['x']+x*math.cos(a)+y*math.sin(a),p['y']-x*math.sin(a)+y*math.cos(a)
def allpads():
 for p in parts:
  for a in F[p['footprint']]['pads']:
   o=dict(a);o['x'],o['y']=transform(p,a['x'],a['y']);o['angle']=p['angle'];o['ref']=p['ref'];o['net']=p['nets'].get(a['num'],'');yield o
B['pads']=list(allpads())
# Header source coordinates retained without rounding or a 2.54 mm Y snap.
B['mechanical_transform']={'x_pcb':'x_gerber + 35.000','y_pcb':'82.000 - y_gerber','rigid_transform':'mirror Y (Gerber Cartesian to CAD screen coordinates) + translation','h1_y_source':26.873,'h2_y_source':6.960,'row_spacing':19.913}
B['pad_lookup']={p['ref']+':'+p['num']:p for p in B['pads'] if p['num']}
ROOT.joinpath('reports/design_model.json').write_text(json.dumps(B,indent=2),encoding='utf-8')
print('Model:',len(parts),'footprints,',len(B['pads']),'pads,',len(B['nets']),'nets.')
