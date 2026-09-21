#!/usr/bin/env python3
"""Reconstruct the candidate's labelled-pin schematic without changing its PCB.

Legacy Device records provide pin names only; the current PCB supplies fitted
components, values, footprints and pin nets. Native exported netlist comparison
is required after generation. This is connectivity documentation, not evidence
of PMIC OTP defaults or a functional sign-off.
"""
from pathlib import Path
import copy
import sys

BASE = Path(__file__).resolve().parents[1]
LEGACY = BASE.parents[1] / 'v0_legacy' / 'tools'
sys.path.insert(0, str(LEGACY))
import generate_evt1 as g
import kicad_sexpr as s

STEM = 'ak_display_38x64_SPLIT_POWER_CANDIDATE'
DATE = '2026-09-20'
original_pin_type = g.pin_type


def pin_type(dev, num):
    if dev.ref == 'U1':
        if num in {'2','5','8','10','11','12','14','15','16','18','19','20','22','25','28','34','35','36'}:
            return 'power_out'
        if num == '26':
            return 'input'
    if dev.ref == 'U2' and num in {'58','59'}:
        return 'bidirectional'  # PC2/PC3 boot straps, not SPI outputs in this board.
    return original_pin_type(dev, num)


def replace_atoms(node, old, new):
    for i, item in enumerate(node):
        if isinstance(item, list):
            replace_atoms(item, old, new)
        elif item == old:
            node[i] = s.Q(new)


def translate(node, dx, dy):
    at = s.child(node, 'at')
    if at:
        at[1:3] = [f'{float(at[1])+dx:.3f}', f'{float(at[2])+dy:.3f}']
    for prop in s.children(node, 'property'):
        translate(prop, dx, dy)


def main():
    g.pin_type = pin_type
    board = s.load(BASE / f'{STEM}.kicad_pcb')
    records = {d.ref: copy.deepcopy(d) for d in g.devices()}
    devices = []
    for fp in s.children(board, 'footprint'):
        props = s.props(fp)
        ref = props['Reference']
        numbered = [p for p in s.children(fp, 'pad') if p[1]]
        if ref not in records:
            assert not numbered, f'No pin-name definition for {ref}'
            continue  # Four mechanical, unnumbered holes; no electrical symbol.
        d = records[ref]
        actual = {}
        for pad in numbered:
            net = s.child(pad, 'net')
            name = str(net[-1]) if net else ''
            actual[str(pad[1])] = None if not name or name.startswith('unconnected-') else name
        assert set(actual) == set(d.pins), ref
        names = {n: v[0] for n, v in d.pins.items()}
        if ref == 'U6':
            names = dict(zip(map(str, range(1,9)), ['~{A}','B','~{CLR}','GND','Q','CEXT','REXT_CEXT','VCC']))
        d.pins = {n: (names[n], net) for n, net in actual.items()}
        d.value = props['Value']
        d.footprint = str(fp[1]).split(':', 1)[-1]
        d.dnp = 'dnp' in s.values(fp, 'attr')
        d.mpn, d.lcsc = props.get('MPN',''), props.get('LCSC','')
        d.note = props.get('Description','')
        d.datasheet = props.get('Datasheet','')
        devices.append(d)
    root_text, sheets = g.root_schematic()
    root = s.loads(root_text)
    s.child(s.child(root,'title_block'),'title')[1] = s.Q('38x64 split-power candidate - connectivity schematic')
    s.child(s.child(root,'title_block'),'comment')[2] = s.Q('Power configuration incomplete: C3036461 factory profile not confirmed')
    s.child(root, 'text')[1] = s.Q('PCB connectivity reconstructed from the current candidate.\nPower targets are requirements, NOT measured/default outputs.\nRead POWER_REVIEW_CN.md before ordering PCBA.\nUSB / TF / wake / display fixes are separate work items.')
    all_libs = []
    for sheet, sheet_uuid in sheets.items():
        tree = s.loads(g.schematic_for_sheet(sheet, devices, g.uid('root-schematic'), sheet_uuid))
        selected = [d for d in devices if d.sheet == sheet]
        # Variable-height column packing prevents USB and SoC symbols overlapping.
        tops = [35.56] * 4
        objects = {s.val(x,'uuid'): x for x in tree if isinstance(x,list) and s.val(x,'uuid')}
        for d in sorted(selected, key=lambda d: -len(d.pins)):
            obj = objects[g.uid('symbol-'+d.ref)]
            half = max(5.08, (((len(d.pins)+1)//2)-1)*2.54/2+1.27)
            col = min(range(4), key=lambda c: tops[c])
            x = 63.5 + 132.08*col
            y = round((tops[col]+half+6.35)/1.27)*1.27
            old = s.child(obj,'at')
            dx, dy = x-float(old[1]), y-float(old[2])
            translate(obj, dx, dy)
            for num in d.pins:
                for prefix in ['label','nc']:
                    label = objects.get(g.uid(f'{prefix}-{d.ref}-{num}'))
                    if label: translate(label, dx, dy)
            tops[col] = y+half+12.7
        assert max(tops) < 365, (sheet,tops)
        # Supply flags certify only physical external feeds and inductor outputs.
        # They do not certify actual voltage, OTP state or load capability.
        for idx in range(6):
            for suffix in ['', '-label']:
                obj = objects.get(g.uid(f'#FLG{idx+1}'+suffix))
                if obj:
                    old = s.child(obj,'at')
                    translate(obj, 50.8+idx*76.2-float(old[1]), 381-float(old[2]))
        all_libs += [copy.deepcopy(x) for x in s.children(s.child(tree,'lib_symbols'),'symbol')]
        for title in [s.child(tree,'title_block')]:
            s.child(title,'date')[1] = s.Q(DATE)
            s.child(title,'rev')[1] = s.Q('PWR-REVIEW1')
            for comment in s.children(title,'comment'):
                if comment[1] == '1': comment[2] = s.Q('Current PCB pin nets; C3036461 factory configuration NOT verified')
        replace_atoms(tree, 'portable_display_epass', STEM)
        filename = {'power':'01_power','soc':'02_soc_v851s','sensors':'03_sensors','interfaces':'04_interfaces'}[sheet]
        s.dump(tree, BASE / f'{filename}.kicad_sch')
    replace_atoms(root, 'portable_display_epass', STEM)
    s.child(s.child(root,'title_block'),'date')[1] = s.Q(DATE)
    s.child(s.child(root,'title_block'),'rev')[1] = s.Q('PWR-REVIEW1')
    s.dump(root, BASE / f'{STEM}.kicad_sch')
    unique = {}
    for symbol in all_libs:
        symbol[1] = s.Q(str(symbol[1]).split(':',1)[-1])
        unique[str(symbol[1])] = symbol
    s.dump(['kicad_symbol_lib',['version','20241209'],['generator',s.Q('candidate_connectivity')],*unique.values()],BASE/'sameat.kicad_sym')
    (BASE/'sym-lib-table').write_text('(sym_lib_table\n (lib (name "Sameat") (type "KiCad") (uri "${KIPRJMOD}/sameat.kicad_sym") (options "") (descr "Candidate connectivity symbols"))\n)\n')
    print(f'Generated {len(devices)} electrical symbols; PCB unchanged.')


if __name__ == '__main__':
    main()
