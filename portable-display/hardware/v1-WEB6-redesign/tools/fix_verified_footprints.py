import copy,json,shutil,sys
from pathlib import Path
from shapely.geometry import box
sys.path.insert(0,'portable-display/hardware/v1-WEB6-redesign/tools')
from plane_connectivity import rb,children,values,val,dumps
from geometry_audit import issues
R=Path('portable-display/hardware/v1-WEB6-redesign');C=R/'split-power-candidate';W=C/'verification/routing_20260910';p=W/'work.kicad_pcb';shutil.copy2(p,W/'before_verified_footprints.kicad_pcb');b=rb.load(p)
fps={next(str(v[2]) for v in children(f,'property') if v[1]=='Reference'):f for f in children(b,'footprint')}
report={};rem=set()
def setv(n,k,v):
 a=children(n,k)
 if a:a[0][1:]=v
 else:n.append([k,*v])
def fab(f,w,h):
 for g in children(f,'fp_rect'):
  if str(val(g,'layer'))=='F.Fab':setv(g,'start',[str(-w/2),str(-h/2)]);setv(g,'end',[str(w/2),str(h/2)])
def court(f,w,h):
 for g in children(f,'fp_rect'):
  if str(val(g,'layer'))=='F.CrtYd':setv(g,'start',[str(-w/2),str(-h/2)]);setv(g,'end',[str(w/2),str(h/2)])
def archive(ref,name,source):
 f=fps[ref];f[1]=rb.q('Sameat:'+name);setv(f,'descr',[rb.q(source)]);lib=copy.deepcopy(f);lib[1]=rb.q(name)
 lib=[n for n in lib if not(isinstance(n,list) and n and n[0] in ['at','uuid','path','sheetname','sheetfile'])]
 lib.insert(2,['version','20240108']);lib.insert(3,['generator',rb.q('pcbnew')])
 for prop in children(lib,'property'):
  if prop[1]=='Reference':prop[2]=rb.q('REF**')
  if prop[1]=='Value':prop[2]=rb.q(name)
  prop[:]=[n for n in prop if not(isinstance(n,list) and n and n[0]=='uuid')]
  a=children(prop,'at')
  if a and len(a[0])>3:a[0][3]='0'
 for pad in children(lib,'pad'):
  pad[:]=[n for n in pad if not(isinstance(n,list) and n and n[0] in ['net','uuid','pinfunction','pintype'])]
  # Local pad orientation, independent of the instance rotation.
  a=children(pad,'at')[0]
  if len(a)>3:a[3]='0'
 (C/'sameat.pretty'/f'{name}.kicad_mod').write_text(dumps(lib)+'\n')
# U1/U2 mechanical outlines only. The package drawing is not a PCB land recommendation.
for ref,dim in [('U1',5),('U2',9)]:
 f=fps[ref];fab(f,dim,dim);report[ref]={'body_mm':[dim,dim],'copper':'unchanged; manufacturer PCB land and EP design still require confirmation'}
 archive(ref,'QFN40' if ref=='U1' else 'QFN88','Body outline corrected using manufacturer package drawing; existing peripheral copper and EP remain provisional')
# U4: ST DS11811 Rev9 pp4,56 + TN0018 Rev8 section3.7.
f=fps['U4'];coords={1:(-.7625,-.75),2:(-.7625,-.25),3:(-.7625,.25),4:(-.7625,.75),5:(-.25,.7625),6:(.25,.7625),7:(.7625,.75),8:(.7625,.25),9:(.7625,-.25),10:(.7625,-.75),11:(.25,-.7625),12:(-.25,-.7625)}
for pad in children(f,'pad'):
 n=int(pad[1]);setv(pad,'at',[str(v) for v in coords[n]]+['0']);setv(pad,'size',['.35','.375'] if n in [5,6,11,12] else ['.375','.35']);setv(pad,'solder_mask_margin',['.05']);setv(pad,'zone_connect',['0'])
fab(f,2,2);court(f,2.5,2.5)
for i in rb.board_items(b):
 if i.kind=='track' and 'F.Cu' in i.layers and i.geom.intersects(box(7.9,4.4,11.1,7.6)):rem.add(i.label)
report['U4']={'layout':'4-2-4-2, top view pin1 upper left','coordinates':coords,'pad_size_mm':[.375,.35],'body_mm':[2,2],'source':'ST DS11811 Rev9 pp4,56; TN0018 Rev8 section3.7'}
archive('U4','LGA-12','ST LIS2DW12 DS11811 Rev9 pp4,56 and TN0018 section3.7; 4-2-4-2 pad positions; https://www.st.com/resource/en/datasheet/lis2dw12.pdf')
for ref,name,cx,sz,body,cyd,src in [
 ('U6','SN74LVC1G123_DCT8',1.9,(1.1,.4),(3,3),(5.4,3.6),'TI DCT0008A 4220784/D 10/2025 board layout, 3.8mm rows; https://www.ti.com/lit/ds/symlink/sn74lvc1g123.pdf'),
 ('U8','TPS22918_DBV6',1.3,(1.1,.6),(1.6,2.9),(4.2,3.45),'TI DBV0006A 4214840/G 08/2024 recommended board layout; https://www.ti.com/lit/ds/symlink/tps22918.pdf'),
 ('U9','USBLC6-2SC6_SOT23-6',1.15,(1.2,.6),(1.625,2.925),(4,3.5),'ST DS4260 Rev7 pp12-13 recommended 1.2x0.6 lands, 2.3mm row centres; https://www.st.com/resource/en/datasheet/usblc6-2.pdf')]:
 f=fps[ref]
 for pad in children(f,'pad'):
  a=children(pad,'at')[0];a[1]=str(-cx if float(a[1])<0 else cx);setv(pad,'size',[str(v) for v in sz])
 fab(f,*body);court(f,*cyd);report[ref]={'row_centres_mm':2*cx,'pad_size_mm':sz,'body_mm':body,'source':src};archive(ref,name,src)
# Remove only copper actually in conflict with corrected pads, then restore affected nets.
its=rb.board_items(b);byid={i.label:i for i in its};affected=set()
for issue in issues(its,clearance=.127):
 if not any(issue[k].split('.')[0] in ['U4','U6','U8','U9'] for k in ['a','b']):continue
 for k in ['a','b']:
  i=byid.get(issue[k])
  if i and i.kind in ['track','via']:rem.add(i.label)
for i in its:
 if i.label in rem:affected.add(i.net)
b=[n for n in b if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'uuid')) in rem)]
p.write_text(dumps(b)+'\n');report['removed_copper']=sorted(rem);report['affected_nets']=sorted(affected);(W/'verified_footprint_changes.json').write_text(json.dumps(report,indent=2)+'\n');print('ripped',len(rem),'items; affected nets:',sorted(affected))
