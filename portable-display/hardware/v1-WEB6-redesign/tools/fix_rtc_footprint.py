#!/usr/bin/env python3
"""Apply the RV-3028-C7 manufacturer's recommended lands, preserving pin nets."""
import copy,json,shutil
from pathlib import Path
from shapely.geometry import box
from plane_connectivity import rb,children,values,val,dumps
from geometry_audit import issues
ROOT=Path(__file__).resolve().parents[1]
CAND=ROOT/'split-power-candidate'; WORK=CAND/'verification/routing_20260910'
BOARD=WORK/'work.kicad_pcb'
SOURCE='https://www.microcrystal.com/fileadmin/Media/Products/RTC/Datasheet/RV-3028-C7.pdf'

def main():
    shutil.copy2(BOARD,WORK/'before_u5_fix.kicad_pcb')
    local=CAND/'sameat.pretty';shutil.copytree(ROOT.parent/'v0_legacy/sameat.pretty',local,dirs_exist_ok=True)
    text=['(footprint "RTC-8" (version 20240108) (generator "pcbnew") (layer "F.Cu")',
          f'(descr "Micro Crystal RV-3028-C7; manufacturer recommended solder lands; datasheet v1.3 pages 1-2; {SOURCE}")',
          '(property "Reference" "REF**" (at 0 -1.7) (layer "F.SilkS") (effects (font (size .7 .7) (thickness .1))))',
          '(property "Value" "RV-3028-C7" (at 0 1.7) (layer "F.Fab") (effects (font (size .7 .7) (thickness .1))))',
          '(attr smd)',
          '(fp_rect (start -1.6 -.75) (end 1.6 .75) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))',
          '(fp_rect (start -1.85 -1.25) (end 1.85 1.25) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))',
          '(fp_circle (center -1.35 .4) (end -1.25 .4) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))',
          '(fp_line (start -1.75 -.75) (end -1.75 .75) (stroke (width .12) (type default)) (layer "F.SilkS"))',
          '(fp_line (start 1.75 -.75) (end 1.75 .75) (stroke (width .12) (type default)) (layer "F.SilkS"))',
          '(fp_poly (pts (xy -1.75 1.05) (xy -1.95 1.05) (xy -1.75 1.25)) (stroke (width .1) (type default)) (fill yes) (layer "F.SilkS"))']
    coordinates={str(i+1):(-1.35+.9*i,.6) for i in range(4)}
    coordinates.update({str(8-i):(-1.35+.9*i,-.6) for i in range(4)})
    for pin,(x,y) in coordinates.items():
        text.append(f'(pad "{pin}" smd rect (at {x:.3f} {y:.3f}) (size .5 .8) (layers "F.Cu" "F.Paste" "F.Mask"))')
    text.append(')');mod=local/'RTC-8.kicad_mod';mod.write_text('\n'.join(text)+'\n')
    (CAND/'fp-lib-table').write_text('(fp_lib_table\n (lib (name "Sameat") (type "KiCad") (uri "${KIPRJMOD}/sameat.pretty") (options "") (descr "Project-local custom footprints; RTC-8 corrected against Micro Crystal datasheet"))\n)\n')
    # The work copy uses the identical library, so DRC sees the deliverable sources.
    (WORK/'fp-lib-table').write_text('(fp_lib_table\n (lib (name "Sameat") (type "KiCad") (uri "${KIPRJMOD}/../../sameat.pretty") (options "") (descr "Candidate project footprints"))\n)\n')
    b=rb.load(BOARD);f=next(f for f in children(b,'footprint') if any(p[1]=='Reference' and p[2]=='U5' for p in children(f,'property')))
    old=copy.deepcopy(f);oldpads={str(p[1]):p for p in children(f,'pad')};new=rb.load(mod);new[1]=rb.q('Sameat:RTC-8')
    # Transfer board identity, component properties and all electrical pin data.
    new=[n for n in new if not(isinstance(n,list) and n and n[0] in ['version','generator','property'])]
    for n in f:
        if isinstance(n,list) and n and n[0] in ['uuid','at','path','property']:new.append(copy.deepcopy(n))
    for pad in children(new,'pad'):
        src=oldpads[str(pad[1])]
        for n in src:
            if isinstance(n,list) and n and n[0] in ['uuid','net','pinfunction','pintype','zone_connect','thermal_bridge_width','thermal_gap']:pad.append(copy.deepcopy(n))
    b[b.index(f)]=new
    before=rb.board_items(b);remove=set();area=box(15.4,5.6,20.2,8.4)
    nets={str(val(p,'net')) for p in oldpads.values()}
    # Rip local pad fanouts. Other board branches remain as routing endpoints.
    for i in before:
        if i.kind=='track' and 'F.Cu' in i.layers and i.net in nets and area.intersects(i.geom):remove.add(i.label)
    for issue in issues(before,clearance=.127):
        if not(issue['a'].startswith('U5.') or issue['b'].startswith('U5.')):continue
        for key in ['a','b']:
            item=next((i for i in before if i.label==issue[key]),None)
            if item and item.kind in ['via','track']:remove.add(item.label)
    b=[n for n in b if not(isinstance(n,list) and n and n[0] in ['segment','via'] and str(val(n,'uuid')) in remove)]
    BOARD.write_text(dumps(b)+'\n')
    result={'source':SOURCE,'source_pages':[1,2],'component':'U5','unchanged_pin_nets':{str(p[1]):str(val(p,'net')) for p in children(new,'pad')},'local_pad_centres_mm':coordinates,'pad_size_mm':[.5,.8],'pitch_mm':.9,'row_centres_mm':1.2,'removed_copper':sorted(remove)}
    (WORK/'u5_fix.json').write_text(json.dumps(result,indent=2)+'\n');print('Replaced U5 footprint; ripped',len(remove),'local copper objects')

if __name__=='__main__':main()
