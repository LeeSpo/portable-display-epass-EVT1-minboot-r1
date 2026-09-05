#!/usr/bin/env python3
"""Structural and approximate-geometry checks, NOT KiCad ERC/DRC.

Checks source/PCB/schematic pin identity, local library identity, UUID uniqueness,
rotation, selected geometry limits, and U2 fanout connectivity. Copper zones,
signal/power integrity and manufacturer package compliance are NOT evaluated.
"""
from __future__ import annotations
import collections, hashlib, json, math
from pathlib import Path
from kicad_sexpr import *
from geometry_audit import board_items, connected_groups, issues
import generate_evt1 as gen
ROOT=Path(__file__).resolve().parents[1]
SHEETS={'power':'01_power.kicad_sch','soc':'02_soc_v851s.kicad_sch','sensors':'03_sensors.kicad_sch','interfaces':'04_interfaces.kicad_sch'}
LIMITATIONS=[
    'No native KiCad parser/ERC/DRC execution in static mode',
    'Zone fills/thermal spokes/zone connectivity are excluded',
    'No mask, courtyard, silkscreen, edge clearance or manufacturability signoff',
    'No impedance, length matching, current capacity, power-sequence or functional validation',
    'Generic footprint dimensions and most component pinouts require datasheet signoff',
]

def walk(a):
    if isinstance(a,list):
        yield a
        for x in a:yield from walk(x)

def unique_uuids(tree):
    counts=collections.Counter(str(x[1]) for x in walk(tree) if x and x[0]=='uuid')
    return {k:n for k,n in counts.items() if n>1}

def snapshot(root=ROOT):
    files=[]
    for pat in ('*.kicad_pcb','*.kicad_sch','*.kicad_pro','*.kicad_sym','*.kicad_dru','*-lib-table','sameat.pretty/*.kicad_mod','tools/*.py','design/*.json'):
        files.extend(root.glob(pat))
    return {str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(set(files)) if f.is_file()}

def netname(node,nets):
    n=values(node,'net')
    return str(n[1]) if len(n)>1 else nets.get(str(n[0]),'') if n else ''

def check_schematic(root,devs):
    problems=[];seenrefs=[];declared=[]
    doc=load(root/'portable_display_epass.kicad_sch');ru=str(val(doc,'uuid'))
    if ru!=gen.uid('root-schematic'):problems.append('Root schematic UUID changed without migration')
    sheets=children(doc,'sheet')
    if len(sheets)!=4:problems.append('Root must instantiate all four expected sheets')
    for s in sheets:
        p=props(s);declared.append(str(p.get('Sheetfile','')))
        inst=child(s,'instances',[])
        paths=[x for x in walk(inst) if x and x[0]=='path']
        if len(paths)!=1 or str(paths[0][1])!='/'+ru:problems.append('Missing or wrong sheet instance parent path')
    if set(declared)!=set(SHEETS.values()):problems.append('Root sheet filenames differ from expected')
    for sheet,filename in SHEETS.items():
        doc=load(root/filename)
        if unique_uuids(doc):problems.append(filename+': duplicate UUIDs')
        if children(doc,'wire') or children(doc,'bus'):
            problems.append(filename+': wired schematic unsupported by direct-pin static checker; native checks required')
        lib={str(x[1]):x for x in children(child(doc,'lib_symbols',[]),'symbol')}
        labels=collections.defaultdict(list);ncs=collections.Counter()
        def pos(node):return tuple(round(float(n),5) for n in values(node,'at')[:2])
        for x in children(doc,'global_label'):labels[pos(x)].append(str(x[1]))
        for x in children(doc,'no_connect'):ncs[pos(x)]+=1
        for s in children(doc,'symbol'):
            ref=str(props(s).get('Reference',''));lid=str(val(s,'lib_id',''))
            if ref.startswith('#FLG'):
                if ref not in {'#FLG1','#FLG2','#FLG3','#FLG4','#FLG5','#FLG6'} or sheet!='power':problems.append('Unexpected supply flag '+ref)
                continue
            seenrefs.append(ref)
            if ref not in devs:problems.append('Unexpected schematic component '+ref);continue
            d=devs[ref]
            if d.sheet!=sheet:problems.append(ref+': wrong sheet')
            if props(s).get('Footprint')!='Sameat:'+d.footprint:problems.append(ref+': schematic footprint mismatch')
            if props(s).get('Value')!=d.value:problems.append(ref+': schematic value mismatch')
            paths=[x for x in walk(child(s,'instances',[])) if x and x[0]=='path']
            if len(paths)!=1 or str(paths[0][1])!='/'+ru+'/'+gen.uid('root-sheet-'+sheet):problems.append(ref+': schematic instance path mismatch')
            if lid not in lib:problems.append(ref+': embedded library missing');continue
            pins=[x for x in walk(lib[lid]) if x and x[0]=='pin']
            actual={str(val(x,'number')):x for x in pins}
            if set(actual)!=set(d.pins) or len(actual)!=len(pins):problems.append(ref+': symbol pin-number set mismatch');continue
            sx,sy,*angle=map(float,values(s,'at'))
            if angle and abs(angle[0])>1e-6:problems.append(ref+': rotated schematic symbol unsupported');continue
            for pn,(name,net) in d.pins.items():
                pin=actual[pn];px,py=map(float,values(pin,'at')[:2]);p=(round(sx+px,5),round(sy-py,5))
                if str(val(pin,'name'))!=name or str(pin[1])!=gen.pin_type(d,pn):problems.append(ref+'.'+pn+': symbol pin metadata mismatch')
                if net:
                    if labels[p]!=[net] or ncs[p]:problems.append(ref+'.'+pn+': label not uniquely connected to intended pin')
                elif labels[p] or ncs[p]!=1:problems.append(ref+'.'+pn+': NC marker missing/ambiguous')
    if set(seenrefs)!=set(devs) or len(seenrefs)!=len(devs):problems.append('Schematic component set incomplete or duplicated')
    return problems

def run(root=ROOT):
    problems=[];devs={d.ref:d for d in gen.devices()}
    b=load(root/'portable_display_epass.kicad_pcb');nets={str(n[1]):str(n[2]) for n in children(b,'net')}
    fps=children(b,'footprint');byref={str(props(f).get('Reference','')):f for f in fps}
    if len(byref)!=len(fps) or set(byref)!=set(devs)|{'H1','H2','H3','H4'}:problems.append('PCB component set incomplete, duplicate, or unexpected')
    if unique_uuids(b):problems.append('PCB duplicate UUIDs')
    contract=json.loads((root/'design/pin_contract.json').read_text())['components']
    observed={d.ref:{'value':d.value,'footprint':'Sameat:'+d.footprint,'sheet':d.sheet,'pins':{pn:{'name':name,'net':net} for pn,(name,net) in d.pins.items()}} for d in devs.values()}
    if contract!=observed:problems.append('Generator pin contract changed: explicit contract review required')
    for ref,d in devs.items():
        if ref not in byref:continue
        f=byref[ref];fp=str(f[1])
        if fp!='Sameat:'+d.footprint:problems.append(ref+': board footprint link mismatch')
        if props(f).get('Value')!=d.value:problems.append(ref+': board value mismatch')
        at=list(map(float,values(f,'at')));at=at+[0.]*(3-len(at))
        if any(abs(v-w)>1e-5 for v,w in zip(at[:2],(d.x,d.y))) or abs((at[2]-d.rotation)%360)>1e-5:problems.append(ref+': source/PCB placement drift')
        expected_path='/'+gen.uid('root-schematic')+'/'+gen.uid('root-sheet-'+d.sheet)+'/'+gen.uid('symbol-'+ref)
        if str(val(f,'path',''))!=expected_path:problems.append(ref+': PCB schematic identity path mismatch')
        pads=children(f,'pad');padsby={str(x[1]):x for x in pads};sourcepads={x.number:x for x in d.pads}
        if len(padsby)!=len(pads) or set(padsby)!=set(d.pins):problems.append(ref+': PCB pad number mismatch');continue
        library=load(root/'sameat.pretty'/(d.footprint+'.kicad_mod'))
        local={str(x[1]):x for x in children(library,'pad')}
        if set(local)!=set(padsby):problems.append(ref+': library pad number mismatch')
        for pn,(name,net) in d.pins.items():
            pad=padsby[pn];p=sourcepads[pn]
            if netname(pad,nets)!=(net or ''):problems.append(ref+'.'+pn+': PCB net mismatch')
            if str(val(pad,'pinfunction',''))!=name or str(val(pad,'pintype',''))!=gen.pin_type(d,pn):problems.append(ref+'.'+pn+': PCB pin metadata mismatch')
            a=list(map(float,values(pad,'at')));a=a+[0.]*(3-len(a))
            if abs(a[0]-p.x)>1e-5 or abs(a[1]-p.y)>1e-5 or abs((a[2]-d.rotation-p.angle)%360)>1e-5:problems.append(ref+'.'+pn+': board pad position/orientation mismatch')
            if any(abs(x-y)>1e-5 for x,y in zip(map(float,values(pad,'size')),(p.sx,p.sy))):problems.append(ref+'.'+pn+': board pad size mismatch')
            if str(pad[2])!=p.kind or str(pad[3])!=p.shape:problems.append(ref+'.'+pn+': pad type/shape mismatch')
            if pn in local:
                lp=local[pn]
                if any(abs(a-b)>0.00006 for a,b in zip(map(float,values(lp,'size')),(p.sx,p.sy))) or any(abs(a-b)>0.00006 for a,b in zip(map(float,values(lp,'at')[:2]),(p.x,p.y))):problems.append(ref+'.'+pn+': local footprint geometry drift')
    problems+=check_schematic(root,devs)
    for name,expected in [('fp-lib-table','${KIPRJMOD}/sameat.pretty'),('sym-lib-table','${KIPRJMOD}/sameat.kicad_sym')]:
        libs=children(load(root/name),'lib')
        if len(libs)!=1 or val(libs[0],'uri')!=expected:problems.append(name+': non-local or extra library configuration')
    items=board_items(b);groups=connected_groups(items);geometry=issues(items)
    if geometry:problems.append(f'{len(geometry)} approximate copper/hole spacing violations')
    # Explicitly refuse unsupported geometry instead of silently claiming coverage.
    if children(b,'arc'):problems.append('Copper arcs are unsupported by static geometry checker')
    if any(str(x.node[3]) not in {'rect','roundrect','circle','oval'} for x in items if x.kind=='pad'):problems.append('Custom pad shapes unsupported')
    if any(tuple(values(x.node,'layers'))!=('F.Cu','B.Cu') for x in items if x.kind=='via'):problems.append('Blind/buried vias unsupported')
    conflicts=[];labels=[];escaped={};netgroups=collections.defaultdict(set)
    for gi,group in enumerate(groups):
        pads=[x for x in group if x.kind=='pad' and x.net]
        pnets={x.net for x in pads};copper=[x for x in group if x.kind!='pad']
        if len(pnets)>1:conflicts.append([x.label+':'+x.net for x in pads])
        if len(pnets)==1 and any(x.net not in pnets for x in copper):labels.append([x.label for x in group])
        for p in pads:
            netgroups[p.net].add(gi)
            if p.ref=='U2' and p.pin!='89' and p.net not in gen.DISPLAY_NETS:
                escaped[p.pin]=any(x.kind=='via' and x.net==p.net for x in group)
    if conflicts:problems.append('Physical copper component joins distinct logical pad nets')
    if labels:problems.append('Copper label differs from its attached logical pad net')
    expected_escape={p for p,(name,net) in devs['U2'].pins.items() if p!='89' and net and net not in gen.DISPLAY_NETS}
    if set(escaped)!=expected_escape or not all(escaped.values()):problems.append('Non-display U2 fanout incomplete')
    opens=[{'net':n,'separate_pad_groups':len(g),'minimum_joins_ignoring_zones':len(g)-1,'display':n in gen.DISPLAY_NETS} for n,g in sorted(netgroups.items()) if len(g)>1]
    return {'schema_version':1,'mode':'STATIC_ONLY','static_checks_passed':not problems,'fabrication_released':False,'native_kicad_executed':False,'source_sha256':snapshot(root),'counts':{'footprints':len(fps),'schematic_components':len(devs),'pads':sum(x.kind=='pad' for x in items),'tracks':sum(x.kind=='track' for x in items),'vias':sum(x.kind=='via' for x in items),'u2_required_fanouts':len(expected_escape),'u2_fanouts_connected_to_via':sum(escaped.values()),'geometric_issues':len(geometry),'copper_net_label_conflicts':len(labels),'multi_net_physical_components':len(conflicts)},'problems':problems,'geometry_issues':geometry,'opens_excluding_zone_connectivity':opens,'limitations':LIMITATIONS}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'verification/static_report.json');a=p.parse_args()
    try:report=run()
    except Exception as e:report={'mode':'STATIC_ONLY','static_checks_passed':False,'fabrication_released':False,'native_kicad_executed':False,'problems':[f'{type(e).__name__}: {e}']}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k in {'mode','counts','problems','static_checks_passed','native_kicad_executed','fabrication_released'}},indent=2))
    raise SystemExit(0 if report['static_checks_passed'] else 1)
