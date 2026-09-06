#!/usr/bin/env python3
"""One-time, checksum-guarded migration of the uploaded PCB, not a router.

Never run on a subsequently edited board. See verification/migration.json.
The source generator in this revision is the target source of pin metadata.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, math
from pathlib import Path
import generate_evt1 as gen
from kicad_sexpr import Q, load, loads, dump, children, child, val, values, props, setval
from geometry_audit import board_items, connected_groups, issues
ROOT=Path(__file__).resolve().parents[1]
BOARD=ROOT/'portable_display_epass.kicad_pcb'


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--apply',action='store_true')
    a.add_argument('--scale',type=float,default=1.65)
    opt=a.parse_args()
    if not opt.apply:a.error('Explicit --apply required; only the original board checksum is accepted')
    manifest=json.loads((ROOT/'reference/import_manifest.json').read_text())
    expected=manifest['source_files'][BOARD.name]
    before=hashlib.sha256(BOARD.read_bytes()).hexdigest()
    if before!=expected:raise SystemExit('Refusing to migrate: board is not the original imported snapshot')
    b=load(BOARD);report={'source_pcb_sha256':before,'u9_net_repairs':[],'moved_components':[],'duplicate_uuid_repairs':[],'fanout_scale':opt.scale,'native_kicad_executed':False}
    netids={str(n[2]):str(n[1]) for n in children(b,'net')}
    devs={d.ref:d for d in gen.devices()}
    # Relabel a chain only when its physically connected logical pad is unique.
    original_items=board_items(b)
    for group in connected_groups(original_items):
        pads=[x for x in group if x.kind=='pad' and x.net]
        if not any(x.ref=='U9' for x in pads):continue
        if len(pads)!=1 or pads[0].ref!='U9':raise ValueError('U9 chain has ambiguous connected pads')
        for x in group:
            if x.kind=='pad' or x.net==pads[0].net:continue
            report['u9_net_repairs'].append({'pad':pads[0].label,'type':x.kind,'old_net':x.net,'new_net':pads[0].net,'old_uuid':x.label})
            setval(x.node,'net',netids[pads[0].net])
    # The original U2 fanout chains connect to no other component. Remove only them.
    remove=set()
    for group in connected_groups(original_items):
        if not any(x.kind=='pad' and x.ref=='U2' and x.pin!='89' for x in group):continue
        foreign=[x.label for x in group if x.kind=='pad' and x.ref!='U2']
        if foreign:raise ValueError(f'Refusing to remove copper connected to {foreign}')
        remove.update(id(x.node) for x in group if x.kind!='pad')
    report['removed_u2_copper']=collections.Counter(x.kind for x in original_items if id(x.node) in remove)
    b[:]=[x for x in b if id(x) not in remove]
    for f in children(b,'footprint'):
        ref=str(props(f).get('Reference',''))
        if ref not in devs:continue
        d=devs[ref]
        if ref=='U8':
            f[:]=loads(gen.footprint_instance(d,{n:int(i) for n,i in netids.items()}))
            report['u8_corrected_pin_count']=len(children(f,'pad'))
        old=list(map(float,values(f,'at')));old=old+[0.]*(3-len(old))
        new=[d.x,d.y,d.rotation]
        if any(abs(x-y)>1e-6 for x,y in zip(old[:2],new[:2])):
            report['moved_components'].append({'ref':ref,'old':old,'new':new})
        setval(f,'at',*(str(v) for v in new))
        setval(f,'path',Q('/'+gen.uid('root-schematic')+'/'+gen.uid('root-sheet-'+d.sheet)+'/'+gen.uid('symbol-'+ref)))
        for p in children(f,'property'):
            if p[1]=='Value':p[2]=Q(d.value)
            if p[1]=='Datasheet':p[2]=Q(d.datasheet)
        sourcepads={p.number:p for p in d.pads}
        for pad in children(f,'pad'):
            pn=str(pad[1]);source=sourcepads[pn];name,net=d.pins[pn]
            setval(pad,'at',str(source.x),str(source.y),str((d.rotation+source.angle)%360))
            setval(pad,'pinfunction',Q(name));setval(pad,'pintype',Q(gen.pin_type(d,pn)))
            if net:setval(pad,'net',netids[net],Q(net))
            else:pad[:]=[x for x in pad if not isinstance(x,list) or x[0]!='net']
    # Splayed single-ring escape: 0.40/0.20 vias, 0.09 mm traces, 0.60 mm straight stubs.
    u=devs['U2'];count=0
    for p in u.pads:
        net=u.pins[p.number][1]
        if not net or net in gen.DISPLAY_NETS or p.number=='89':continue
        px,py=gen.abs_pad(u,p)
        ox,oy=gen.pad_outward(u,p)
        sx,sy=px+ox*.60,py+oy*.60
        vx,vy=u.x+p.x*opt.scale,u.y+p.y*opt.scale
        tag=f'r1-u2-{p.number}'
        b.append(loads(gen._seg(px,py,sx,sy,.09,'F.Cu',net,netids,tag+'-stub')))
        b.append(loads(gen._seg(sx,sy,vx,vy,.09,'F.Cu',net,netids,tag+'-escape')))
        b.append(loads(f'(via (at {vx:.5f} {vy:.5f}) (size .40) (drill .20) (layers "F.Cu" "B.Cu") (net {netids[net]}) (uuid "{gen.uid(tag+"-via")}"))'))
        count+=1
    report['generated_non_display_u2_fanouts']=count
    # Old _seg(tag) reused UUIDs for different geometry. Preserve first, replace duplicates.
    seen=set()
    def repair(node):
        if not isinstance(node,list):return
        if node and node[0]=='uuid':
            old=str(node[1]);new=old
            if old in seen:
                new=gen.uid(f'r1-duplicate-{old}-{len(report["duplicate_uuid_repairs"])}')
                report['duplicate_uuid_repairs'].append({'old':old,'new':new});node[1]=Q(new)
            seen.add(new)
        for x in node:repair(x)
    repair(b)
    # Cached zone fills cannot remain valid after geometry edits.
    for zone in children(b,'zone'):
        zone[:]=[x for x in zone if not isinstance(x,list) or x[0] not in {'filled_polygon','fill_segments'}]
    setval(child(b,'setup'),'aux_axis_origin','0','110')
    setval(b,'generator',Q('sameat-evt1-r1'));setval(b,'generator_version',Q('r1'))
    for t in children(b,'gr_text'):
        if 'Portable Display V1.0' in str(t[1]):t[1]=Q('Portable Display EVT1-minboot-r1\nENGINEERING ONLY - NOT FOR FABRICATION')
    found=issues(board_items(b))
    report['static_geometry_issues']=found
    if found:
        (ROOT/'verification/migration_candidate.json').write_text(json.dumps(report,indent=2)+'\n')
        dump(b,ROOT/'verification/migration_candidate.kicad_pcb')
        print(json.dumps({'fanout':count,'issues':len(found),'types':dict(collections.Counter(x['type'] for x in found)),'sample':found[:10]},indent=2))
        raise SystemExit('Candidate has static geometry issues; original PCB preserved')
    dump(b,BOARD)
    report['result_pcb_sha256']=hashlib.sha256(BOARD.read_bytes()).hexdigest()
    (ROOT/'verification/migration.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['u9_net_repairs','duplicate_uuid_repairs']},indent=2))

if __name__=='__main__':main()
