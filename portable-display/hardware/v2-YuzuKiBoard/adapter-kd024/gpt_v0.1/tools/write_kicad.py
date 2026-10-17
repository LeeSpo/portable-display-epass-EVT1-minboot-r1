#!/usr/bin/env python3
"""Write editable KiCad 8-target S-expressions from reviewed source model.
No KiCad executable is invoked here. Native parse/ERC/DRC remain release gates.
"""
from geometry import *
import json,uuid,math,re,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]; K=ROOT/'kicad';b=load()
NS=uuid.UUID('e10b7820-c443-4dbe-85f3-85ecbf0d4a44')
def uid(s):return str(uuid.uuid5(NS,s))
def q(s):return json.dumps(str(s),ensure_ascii=False)
def n(x):return f'{float(x):.6f}'.rstrip('0').rstrip('.') or '0'
def eff(size=1.0,just='',hide=False):return f'(effects (font (size {n(size)} {n(size)}))'+(f' (justify {just})' if just else '')+(' hide' if hide else '')+')'
rootid=uid('schematic:root'); sheets={'root':('adapter_v0.1.kicad_sch',rootid),'bias':('power_bias.kicad_sch',uid('schematic:bias')),'logic':('logic_control.kicad_sch',uid('schematic:logic'))}; sheetids={s:uid('sheet_instance:'+s) for s in ['bias','logic']}
netids={s:i+1 for i,s in enumerate(b['nets'])}
# Simple, explicit symbols. All pins have declared electrical types.
def symgeometry(name,pins):
 if name in ['R','C','L']:
  return {'w':5.08,'h':2.54,'pins':[{'num':str(i),'name':na,'type':ty,'x':-5.08 if i==1 else 5.08,'y':0,'angle':0 if i==1 else 180,'length':2.54 if name!='C' else 4.445} for i,na,ty in pins]}
 if name in ['TP','PWR_FLAG']:return {'w':1.27,'h':1.27,'pins':[{'num':'1','name':pins[0][1],'type':pins[0][2],'x':-2.54,'y':0,'angle':0,'length':2.54}]}
 if name=='Mechanical':return {'w':2.0,'h':2.0,'pins':[]}
 connector=name in ['J1','J2','H13','H5']; w=15.24 if connector else 13.97
 pp=[]
 groups=[pins] if connector else [pins[:math.ceil(len(pins)/2)],pins[math.ceil(len(pins)/2):]]
 for side,group in enumerate(groups):
  right=connector or side==1
  for j,(i,na,ty) in enumerate(group):
   pp.append({'num':str(i),'name':na,'type':ty,'x':w+5.08 if right else -w-5.08,'y':((len(group)-1)/2-j)*2.54,'angle':180 if right else 0,'length':5.08})
 return {'w':w,'h':max(len(x) for x in groups)*2.54/2+1.27,'pins':pp}
spec={k:symgeometry(k,v) for k,v in b['pin_contracts'].items()}
def libsymbol(name,embedded=False):
 s=spec[name];body=[];w,h=s['w'],s['h'];passive=name in ['R','C','L']
 headname='Adapter:'+name if embedded else name
 body.append(f'(symbol {q(headname)} (pin_names (offset 0.762)'+(' hide' if passive else '')+') (in_bom '+('no' if name=='PWR_FLAG' else 'yes')+') (on_board '+('no' if name=='PWR_FLAG' else 'yes')+')')
 body += [f'(property "Reference" "{ "#FLG" if name=="PWR_FLAG" else "REF" }" (at 0 {n(h+3.81)} 0) {eff(1.27)})',f'(property "Value" {q(name)} (at 0 {n(h+1.27)} 0) {eff(1.0)})']
 shapes=[]
 if name=='R':shapes.append('(rectangle (start -2.54 0.9) (end 2.54 -0.9) (stroke (width 0.254) (type default)) (fill (type none)))')
 elif name=='C':
  for x in [-.635,.635]:shapes.append(f'(polyline (pts (xy {x} -1.524) (xy {x} 1.524)) (stroke (width 0.254) (type default)) (fill (type none)))')
 elif name=='L':
  pts=[(-2.54+i*5.08/32, .75*abs(math.sin(i*math.pi/8))) for i in range(33)]
  shapes.append('(polyline (pts '+' '.join(f'(xy {n(x)} {n(y)})' for x,y in pts)+') (stroke (width 0.254) (type default)) (fill (type none)))')
 elif name in ['TP','Mechanical','PWR_FLAG']:
  shapes.append('(circle (center 0 0) (radius 1.0) (stroke (width 0.254) (type default)) (fill (type none)))')
 else:shapes.append(f'(rectangle (start {-w} {h}) (end {w} {-h}) (stroke (width 0.254) (type default)) (fill (type background)))')
 body.append(f'(symbol {q(name+"_0_1")} '+' '.join(shapes)+')')
 ps=[]
 for p in s['pins']:
  ps.append(f'(pin {p["type"]} line (at {n(p["x"])} {n(p["y"])} {p["angle"]}) (length {n(p["length"])}) (name {q(p["name"])} {eff(1.0)}) (number {q(p["num"])} {eff(.95)}))')
 body.append(f'(symbol {q(name+"_1_1")} '+' '.join(ps)+')')
 return '\n'.join(body)+')'
(K/'Adapter.kicad_sym').write_text('(kicad_symbol_lib (version 20220914) (generator adapter_review_generator)\n'+'\n'.join(libsymbol(x) for x in spec)+'\n)')
(K/'sym-lib-table').write_text('(sym_lib_table\n (lib (name "Adapter") (type "KiCad") (uri "${KIPRJMOD}/Adapter.kicad_sym") (options "") (descr "Project-owned, source-cited symbols"))\n)\n')
(K/'fp-lib-table').write_text('(fp_lib_table\n (lib (name "Adapter") (type "KiCad") (uri "${KIPRJMOD}/Adapter.pretty") (options "") (descr "Project-owned, source-cited engineering footprints"))\n)\n')
# Schematic placements, four controlled power domains remain distinct.
places={'J1':(62,86),'J2':(245,108),'H1':(61,180),'H2':(151,177),'U1':(252,66),'U2':(65,64),'U3':(72,63),'U4':(250,63),
'L1':(220,32),'L2':(342,103),'R1':(148,65),'R2':(70,108),'R3':(65,108),'R4':(65,141),'R5':(249,107),'R6':(176,111),'R7':(325,109),'R8':(323,149),'R9':(345,65)}
for ref,xy in {'C1':(42,181),'C2':(111,181),'C3':(42,215),'C4':(111,215),'C5':(185,148),'C6':(185,184),'C7':(254,148),'C8':(254,184),'C9':(344,141),'C10':(344,177),'C11':(344,213),'C12':(255,219),'C13':(44,154),'C14':(112,154),'C15':(44,194),'C16':(112,194),'C17':(245,151)}.items():places[ref]=xy
for i in range(18,24):places[f'C{i}']=(42+65*(i-18),234)
for i,r in enumerate(['TP1','TP2','TP3','TP4','TP7']):places[r]=(40+i*73,255)
for i,r in enumerate(['TP5','TP6','TP8','TP9','TP10','TP11','TP12']):places[r]=(35+i*57,234)
for i,r in enumerate(['MH1','MH2','MH3','MH4','FID1','FID2']):places[r]=(40+i*57,266)
# Coordinates of all pin/net graphical endpoints are saved for PDF rendering and graph checks.
viewdata={}; flags={'root':[('VBUS_5V',30,281),('HOST_3V3_LOGIC',127,281),('PANEL_VCI_3V3',240,281),('GND',365,281)],'bias':[('BIAS_IN_3V6',145,105)],'logic':[('LOGIC_LDO_IN',166,194)]}
for sec,(filename,sid) in sheets.items():
 items=[p for p in b['parts'] if p['section']==sec]
 used={p['symbol'] for p in items}|({'PWR_FLAG'} if flags[sec] else set())
 out=[f'(kicad_sch (version 20231120) (generator adapter_review_generator) (uuid {sid}) (paper "A3")', '(lib_symbols '+'\n'.join(libsymbol(s,True) for s in sorted(used))+')']
 title={'root':'HOST / PANEL INTERFACES','bias':'5 V PREREGULATOR / TPS65631 BIAS','logic':'1.8 V LOGIC / RESET / TEST ACCESS'}[sec]
 texts=[(18,14,2.1,'LIZARD - KD024  |  '+title),(18,22,1.3,'v0.1-review.1  |  ENGINEERING HOLD  |  ERC / DRC NOT RUN')]
 if sec=='root':texts += [(107,48,1.0,'FFC identity mapping is a conditional design assumption.'),(107,53,1.0,'Never power an unverified cable. LEDA / LEDK stay NC.'),(107,58,1.0,'H1 / H2: bottom mating, manual fit / assembly DNP.'),(107,63,1.0,'DSI lanes: only D0 and CK. No D1 or backlight nets.'),(326,167,1.0,'IM0 = IM1 = 0; MTP = GND.'),(326,173,1.0,'Pins 18-29 on J2: intentionally NC.')]
 if sec=='bias':texts += [(107,36,1.05,'U2: 0.8 * (1 + 34.8k / 10k) = 3.584 V nominal'),(107,42,1.05,'Do not apply host 5 V to U1 directly.'),(174,121,1.0,'R5 = 10k: bias defaults OFF.'),(174,126,1.0,'R9: Kelvin sense from C9 positive to FBS.'),(22,275,1.05,'U1 defaults: +4.6 V / -4.0 V. Panel vendor must approve before CTRL is driven HIGH.')]
 if sec=='logic':texts += [(170,31,1.0,'PD8 3.3 V -> U4 at 1.8 V -> RESX; input tolerant.'),(170,37,1.0,'VCI is separate from LCD_EN; no bias pulses on VCI.'),(175,174,1.0,'R8 DNP: panel SWIRE is an OUTPUT, not a host input.'),(175,180,1.0,'TE and TE1 are probe-only. No DSI probe stubs.'),(22,267,1.05,'Rail sequencing and RM690B0 initialization require a panel-approved MIPI procedure.')]
 for i,(x,y,size,txt) in enumerate(texts):out.append(f'(text {q(txt)} (at {x} {y} 0) {eff(size,"left")} (uuid {uid(sec+":text:"+str(i))}))')
 views=[]
 for p in items:
  x,y=places[p['ref']];p['sch_xy']=[x,y];s=spec[p['symbol']];h=s['h'];ppath='/'+rootid+('' if sec=='root' else '/'+sheetids[sec]);
  st=[f'(symbol (lib_id {q("Adapter:"+p["symbol"])}) (at {x} {y} 0) (unit 1) (in_bom {"no" if p["feature"] else "yes"}) (on_board yes) (dnp {"yes" if p["dnp"] else "no"}) (uuid {p["uuid"]})']
  st += [f'(property "Reference" {q(p["ref"])} (at {x} {n(y-h-6.35)} 0) {eff(1.3)})',f'(property "Value" {q(p["value"])} (at {x} {n(y-h-3.81)} 0) {eff(.95)})',f'(property "Footprint" {q("Adapter:"+p["footprint"])} (at {x} {y} 0) {eff(1.0,hide=True)})',f'(property "LCSC" {q(p["lcsc"])} (at {x} {y} 0) {eff(1.0,hide=True)})']
  vp=[]
  for pin in s['pins']:
   st.append(f'(pin {q(pin["num"])} (uuid {uid(p["ref"]+":pin:"+pin["num"])}))')
   px=x+pin['x'];py=y-pin['y'];net=p['nets'].get(pin['num']);right=pin['x']>0;ex=px+(3.81 if right else -3.81)
   if net:
    out.append(f'(wire (pts (xy {n(px)} {n(py)}) (xy {n(ex)} {n(py)})) (stroke (width 0) (type default)) (uuid {uid("wire:"+p["ref"]+":"+pin["num"])}))')
    out.append(f'(global_label {q(net)} (shape input) (at {n(ex)} {n(py)} {0 if right else 180}) {eff(.95,"left" if right else "right")} (uuid {uid("label:"+p["ref"]+":"+pin["num"])}))')
   else:out.append(f'(no_connect (at {n(px)} {n(py)})(uuid {uid("nc:"+p["ref"]+":"+pin["num"])}))')
   vp.append(dict(pin,x=px,y=py,label_x=ex,net=net))
  st.append(f'(instances (project "adapter_v0.1" (path {q(ppath)} (reference {q(p["ref"])}) (unit 1))))')
  out.append('\n'.join(st)+')');views.append({'part':p,'geom':s,'pins':vp})
 for i,(net,x,y) in enumerate(flags[sec]):
  ref=f'#FLG{ {"root":100,"bias":200,"logic":300}[sec]+i }';si=uid(ref);ppath='/'+rootid+('' if sec=='root' else '/'+sheetids[sec]);pinx=x-2.54
  out.append(f'(symbol (lib_id "Adapter:PWR_FLAG") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid {si}) (property "Reference" {q(ref)} (at {x} {y-3} 0) {eff(.8,hide=True)}) (property "Value" "PWR_FLAG" (at {x} {y-3} 0) {eff(.8)}) (pin "1" (uuid {uid(ref+":pin")})) (instances (project "adapter_v0.1" (path {q(ppath)} (reference {q(ref)}) (unit 1)))))')
  out.append(f'(global_label {q(net)} (shape input) (at {n(pinx)} {y} 180) {eff(.85,"right")} (uuid {uid(ref+":label")}))')
 if sec=='root':
  for j,ss in enumerate(['bias','logic']):
   x,y=335,64+j*55
   out.append(f'(sheet (at {x} {y}) (size 63 23) (fields_autoplaced) (stroke (width 0.1524) (type default)) (fill (color 0 0 0 0)) (uuid {sheetids[ss]}) (property "Sheetname" {q(ss.upper())} (at {x} {y-2} 0) {eff(1.27,"left")}) (property "Sheetfile" {q(sheets[ss][0])} (at {x} {y+25} 0) {eff(1.0,"left")}) (instances (project "adapter_v0.1" (path {q("/"+rootid)} (page "{j+2}")))))')
  out.append('(sheet_instances (path "/" (page "1")))')
 out.append(')');(K/filename).write_text('\n'.join(out),encoding='utf-8');viewdata[sec]={'title':title,'texts':texts,'items':views,'flags':flags[sec]}
(ROOT/'reports/schematic_views.json').write_text(json.dumps(viewdata,indent=2))
# Footprints and board.
def fpwrite(name,p=None):
 d=b['footprints'][name];inside=p is not None
 ref=p['ref'] if p else 'REF**';ang=p['angle'] if p else 0;fpname='Adapter:'+name if inside else name
 s=[f'(footprint {q(fpname)}'+('' if inside else ' (version 20240108) (generator adapter_review_generator)'),'(layer "F.Cu")',f'(descr {q(d["source"])})']
 if inside:
  sec=p['section'];path='/'+('' if sec=='root' else sheetids[sec]+'/')+p['uuid'];
  s += [f'(tstamp {p["footprint_uuid"]})',f'(at {n(p["x"])} {n(p["y"])} {ang})',f'(path {q(path)})']
  for key,val in [('LCSC',p['lcsc']),('MPN',p['mpn']),('LibraryClass',p['library_class']),('Assembly','COPPER_FEATURE' if p['feature'] else 'DNP_MANUAL' if p['dnp'] else 'TOP_FIT')]:s.append(f'(property {q(key)} {q(val)})')
 attr='through_hole' if name.startswith('Header') else 'exclude_from_pos_files exclude_from_bom' if p and p['feature'] else 'smd'
 if p and p['dnp']:attr += ' dnp exclude_from_pos_files'
 s.append('(attr '+attr+')')
 bb=d['body'];allx=[a['x']-a['w']/2 for a in d['pads']]+[bb[0]];allxx=[a['x']+a['w']/2 for a in d['pads']]+[bb[2]];ally=[a['y']-a['h']/2 for a in d['pads']]+[bb[1]];allyy=[a['y']+a['h']/2 for a in d['pads']]+[bb[3]]
 x0,y0,x1,y1=min(allx)-.25,min(ally)-.25,max(allxx)+.25,max(allyy)+.25
 s += [f'(fp_text reference {q(ref)} (at 0 {n(y0-.7)} {ang}) (layer "F.Fab") {eff(.65)})',f'(fp_text value {q(p["value"] if p else name)} (at 0 {n(y1+.7)} {ang}) (layer "F.Fab") hide {eff(.65)})']
 for layer,w,rect in [('F.Fab',.10,bb),('F.CrtYd',.05,[x0,y0,x1,y1])]:
  s.append(f'(fp_rect (start {n(rect[0])} {n(rect[1])}) (end {n(rect[2])} {n(rect[3])}) (stroke (width {w}) (type solid)) (fill none) (layer {q(layer)}))')
 for a in d['pads']:
  net=p['nets'].get(a['num']) if inside else None
  ptype=a['kind'];dr=f'(drill {n(a["drill"])})' if a.get('drill') else ''
  lays=' '.join(q(x) for x in a['layers'])
  ns=f'(net {netids[net]} {q(net)})' if net else ''
  s.append(f'(pad {q(a["num"])} {ptype} {a["shape"]} (at {n(a["x"])} {n(a["y"])} {ang}) (size {n(a["w"])} {n(a["h"])}) {dr} (layers {lays}) {ns})')
 for x,y,w,h in d['paste_windows']:
  s.append(f'(pad "" smd rect (at {n(x)} {n(y)} {ang}) (size {n(w)} {n(h)}) (layers "F.Paste"))')
 if name.startswith('Fiducial'):s.append('(pad "" smd circle (at 0 0) (size 2 2) (layers "F.Mask"))')
 if name.startswith(('Hirose_','Molex_','TI_','Coilcraft_')):
  s.append(f'(model "${{KIPRJMOD}}/models/{name}.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))')
 s.append(')');return '\n'.join(s)
for name in b['footprints']:(K/'Adapter.pretty'/f'{name}.kicad_mod').write_text(fpwrite(name))
board=[ '(kicad_pcb (version 20240108) (generator adapter_review_generator)', '(general (thickness 1))', '(paper "A4")',
 '(layers (0 "F.Cu" signal) (1 "In1.Cu" power) (2 "In2.Cu" mixed) (31 "B.Cu" signal) (32 "B.Adhes" user "B.Adhesive") (33 "F.Adhes" user "F.Adhesive") (34 "B.Paste" user) (35 "F.Paste" user) (36 "B.SilkS" user "B.Silkscreen") (37 "F.SilkS" user "F.Silkscreen") (38 "B.Mask" user) (39 "F.Mask" user) (40 "Dwgs.User" user "User.Drawings") (41 "Cmts.User" user "User.Comments") (44 "Edge.Cuts" user) (46 "B.CrtYd" user "B.Courtyard") (47 "F.CrtYd" user "F.Courtyard") (48 "B.Fab" user) (49 "F.Fab" user))',
 '(setup (pad_to_mask_clearance 0.05) (solder_mask_min_width 0) (aux_axis_origin 50 82) (grid_origin 50 82))', '(net 0 "")']
board += [f'(net {i} {q(nm)})' for nm,i in netids.items()]
board += [fpwrite(p['footprint'],p) for p in b['parts']]
for i,t in enumerate(b['tracks']):board.append(f'(segment (start {n(t["a"][0])} {n(t["a"][1])}) (end {n(t["b"][0])} {n(t["b"][1])}) (width {n(t["width"])}) (layer {q(t["layer"])}) (net {netids[t["net"]]}) (tstamp {uid("track:"+str(i))}))')
for i,v in enumerate(b['vias']):board.append(f'(via (at {n(v["x"])} {n(v["y"])}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {netids[v["net"]]}) (tstamp {uid("via:"+str(i))}))')
x0,y0,x1,y1=b['board']
for i,(a,c) in enumerate([((x0,y0),(x1,y0)),((x1,y0),(x1,y1)),((x1,y1),(x0,y1)),((x0,y1),(x0,y0))]):board.append(f'(gr_line (start {a[0]} {a[1]}) (end {c[0]} {c[1]}) (stroke (width 0.05) (type default)) (layer "Edge.Cuts") (tstamp {uid("edge:"+str(i))}))')
# Explicit circular mechanical keepouts on all copper layers.
for i,(x,y,dr,r) in enumerate(b['holes']):
 pts=[(x+r*math.cos(j*math.pi/32),y+r*math.sin(j*math.pi/32)) for j in range(64)]
 board.append(f'(zone (net 0) (net_name "") (layers "F.Cu" "In1.Cu" "In2.Cu" "B.Cu") (tstamp {uid("keepout:"+str(i))}) (hatch edge 0.5) (connect_pads (clearance 0)) (min_thickness 0.15) (keepout (tracks not_allowed) (vias not_allowed) (pads not_allowed) (copperpour not_allowed) (footprints allowed)) (fill (thermal_gap 0.3) (thermal_bridge_width 0.3)) (polygon (pts '+ ' '.join(f'(xy {n(a)} {n(c)})' for a,c in pts)+')))')
 board.append(f'(gr_circle (center {x} {y}) (end {n(x+r)} {y}) (stroke (width 0.1) (type dash)) (fill none) (layer "Dwgs.User"))')
# Ground zones have no assumed dielectric/impedance values. They must be refilled by KiCad.
for layer in ['F.Cu','In1.Cu','In2.Cu','B.Cu']:
 board.append(f'(zone (net {netids["GND"]}) (net_name "GND") (layer {q(layer)}) (tstamp {uid("ground:"+layer)}) (hatch edge 0.5) (connect_pads yes (clearance 0.15)) (min_thickness 0.15) (fill yes (thermal_gap 0.25) (thermal_bridge_width 0.2)) (polygon (pts (xy 50.3 44.3) (xy 91.7 44.3) (xy 91.7 81.7) (xy 50.3 81.7))))')
# Silkscreen marks are placed with a geometric exclusion against all pads and vias.
copper=[pad_shape(a) for a in b['pads']]+[via_shape(v) for v in b['vias']]
marks=[]
for ref in ['J1','J2','U1','U2','U3','U4']:
 p=next(p for p in b['parts'] if p['ref']==ref);a=next(a for a in b['pads'] if a['ref']==ref and a['num']=='1')
 found=None
 for dx,dy in [(0,-1),(-.8,-.6),(.8,-.6),(-1,0),(1,0),(-1,-1),(1,1),(-1.3,-.6),(1.3,-.6)]:
  x,y=a['x']+dx,a['y']+dy;g=Point(x,y).buffer(.14)
  if not box(x0+.2,y0+.2,x1-.2,y1-.2).covers(g):continue
  if all(g.distance(s)>=.18 for s in copper):found=(x,y);break
 if found:
  x,y=found;board.append(f'(gr_circle (center {n(x)} {n(y)}) (end {n(x+.1)} {n(y)}) (stroke (width 0.08) (type default)) (fill solid) (layer "F.SilkS"))');marks.append({'ref':ref,'kind':'pin1_dot','x':x,'y':y,'rotation':p['angle']})
for x,ystart,yend in [(65.3022,81.9,81.4),(76.5,44.1,44.65)]:
 dy=1 if yend>ystart else -1
 for a,c in [((x,ystart),(x,yend)),((x,yend),(x-.25,yend-.2*dy)),((x,yend),(x+.25,yend-.2*dy))]:
  board.append(f'(gr_line (start {n(a[0])} {n(a[1])}) (end {n(c[0])} {n(c[1])}) (stroke (width 0.10) (type default)) (layer "F.SilkS"))')
# Reference labels use F.Fab to avoid ink over fine connector contacts / vias.
board.append('(gr_text "J1  -  VERIFY FFC" (at 65.3022 79.2) (layer "F.SilkS") (effects (font (size 0.65 0.65) (thickness 0.10))))')
board.append('(gr_text "v0.1 REVIEW ONLY - NO FAB RELEASE" (at 73 85) (layer "Dwgs.User") (effects (font (size 1 1) (thickness 0.15))))')
board.append('(gr_text "DSI W/S: PENDING OFFICIAL JLC RESULT; 4 NETS UNROUTED" (at 72 42) (layer "Dwgs.User") (effects (font (size 0.8 0.8) (thickness 0.12))))')
board.append(')');(K/'adapter_v0.1.kicad_pcb').write_text('\n'.join(board))
b['pin1_marks']=marks;save(b)
pro={'meta':{'filename':'adapter_v0.1.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.15,'min_track_width':.15,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_copper_edge_clearance':.3,'min_hole_clearance':.25,'min_hole_to_hole':.25},'defaults':{'copper_line_width':.15,'edge_cuts_line_width':.05,'silk_line_width':.1,'silk_text_size_h':.8,'silk_text_size_v':.8,'silk_text_thickness':.12},'drc_exclusions':[],'track_widths':[.15,.25,.4,.6],'via_dimensions':[{'diameter':.6,'drill':.3}]}},'net_settings':{'classes':[{'name':'Default','clearance':.15,'track_width':.15,'via_diameter':.6,'via_drill':.3,'microvia_diameter':.2,'microvia_drill':.1}], 'meta':{'version':3}},'schematic':{'drawing':{'default_line_thickness':6.0}},'text_variables':{'FABRICATION_RELEASE':'HOLD','TARGET_STACKUP':'JLC04101H-3313; dielectric data UNVERIFIED','DSI_IMPEDANCE':'UNVERIFIED; NO ROUTES'}}
(K/'adapter_v0.1.kicad_pro').write_text(json.dumps(pro,indent=2))
(K/'adapter_v0.1.kicad_dru').write_text('''(version 1)
(rule "Minimum copper clearance" (constraint clearance (min 0.15mm)))
(rule "Minimum trace width" (constraint track_width (min 0.15mm)))
(rule "Copper to edge" (constraint edge_clearance (min 0.3mm)))
(rule "Through vias" (condition "A.Type == 'Via'") (constraint via_diameter (min 0.6mm)) (constraint hole_size (min 0.3mm)))
(rule "DSI on Top only" (condition "A.NetName == 'DSI_D0_P' || A.NetName == 'DSI_D0_N' || A.NetName == 'DSI_CK_P' || A.NetName == 'DSI_CK_N'") (layer "inner") (constraint disallow track via))
(rule "No DSI on Bottom" (condition "A.NetName == 'DSI_D0_P' || A.NetName == 'DSI_D0_N' || A.NetName == 'DSI_CK_P' || A.NetName == 'DSI_CK_N'") (layer "B.Cu") (constraint disallow track via))
(rule "No DSI vias" (condition "A.Type == 'Via' && (A.NetName == 'DSI_D0_P' || A.NetName == 'DSI_D0_N' || A.NetName == 'DSI_CK_P' || A.NetName == 'DSI_CK_N')") (constraint disallow via))
# Differential width, spacing and skew constraints cannot be signed off until
# actual stackup and the official 100-ohm calculator result are provided.
''')
print('Wrote 3 schematics, PCB, project, symbols,',len(b['footprints']),'footprints. Native KiCad validation NOT RUN.')
