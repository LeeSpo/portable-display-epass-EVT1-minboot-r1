#!/usr/bin/env python3
"""Reconstruct the candidate's labelled-pin schematic without changing its PCB.

Legacy Device records provide pin names only; the current PCB supplies fitted
components, values, footprints and pin nets. Native exported netlist comparison
is required after generation. This is connectivity documentation, not evidence
of PMIC OTP defaults or a functional sign-off.
"""
from pathlib import Path
import copy

BASE = Path(__file__).resolve().parents[1]
import schematic_support as g
import kicad_sexpr as s

STEM = 'ak_display_38x64_SPLIT_POWER_CANDIDATE'
EXTRA_SUPPLY_NETS = ('3V3_PMIC', '3V3_B', 'CORE_0V93_PMIC', 'DRAM_1V5_PMIC', '1V8')
DATE = '2026-10-18'
original_pin_type = g.pin_type


def pin_type(dev, num):
    if dev.ref == 'U11':
        return {'1': 'input', '2': 'power_in', '3': 'input',
                '4': 'output', '5': 'power_in', '6': 'output'}[num]
    if dev.ref in ('U12', 'U13'):
        return 'power_in' if num in ('3', '8') else 'passive'
    if dev.ref == 'U1':
        if num in {'2','5','8','10','11','12','14','15','16','18','19','20','22','25','28','34','35','36'}:
            return 'power_out'
        if num == '26':
            return 'input'
    if dev.ref == 'U2' and num in {'56','58','59'}:
        return 'bidirectional'  # PC1 FEL input and PC2/PC3 boot straps at reset.
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
    records['R32'] = copy.deepcopy(records['R20'])
    records['R32'].ref = 'R32'
    records['R32'].sheet = 'interfaces'
    records['C52'] = copy.deepcopy(records['C26'])
    records['C52'].ref = 'C52'
    for ref in ['C53', 'C54', 'C55', 'C56', 'C57', 'C58', 'C59', 'C60', 'C61', 'C62', 'C63', 'C64']:
        records[ref] = copy.deepcopy(records['C26'])
        records[ref].ref = ref
    for ref in ['R33', 'R34', 'R35', 'R36', 'R37', 'R38', 'R39', 'R40']:
        records[ref] = copy.deepcopy(records['R10'])
        records[ref].ref = ref
    for ref in ['U12', 'U13']:
        records[ref] = g.Device(ref, 'TPD4E05U06DQAR', 'TPD4E05U06_DQA',
                                'interfaces', 0, 0,
                                {str(n): (name, None) for n, name in enumerate(
                                    ['IO1', 'IO2', 'GND', 'IO3', 'IO4',
                                     'NC_FT4', 'NC_FT3', 'GND', 'NC_FT2', 'NC_FT1'], 1)})
    records['J5'].pins = {str(n): (name, None) for n, name in enumerate(
        ['DAT2', 'CD_DAT3', 'CMD', 'VDD', 'CLK', 'VSS', 'DAT0', 'DAT1', 'DET',
         'SHIELD', 'SHIELD', 'SHIELD', 'SHIELD'], 1)}
    records['U11'] = g.Device('U11', 'SN74LVC2G17DBVR', 'SN74LVC2G17_DBV6',
                             'sensors', 0, 0,
                             {str(n): (name, None) for n, name in enumerate(
                                 ['1A', 'GND', '2A', '2Y', 'VCC', '1Y'], 1)})
    devices = []
    for fp in s.children(board, 'footprint'):
        props = s.props(fp)
        ref = props['Reference']
        numbered = [p for p in s.children(fp, 'pad') if p[1]]
        if ref.startswith('TP') and str(fp[1]) == 'Sameat:TestPoint_Pad_D1.0mm':
            net = str(s.val(s.children(fp, 'pad')[0], 'net'))
            test_sheets = {'CORE_0V93': 'soc', 'DRAM_1V5': 'soc', '1V8': 'soc',
                           'RTC_3V3': 'sensors', 'VSYS': 'power', 'ELVDD': 'interfaces',
                           'ELVSS': 'interfaces', 'PMIC_SCL': 'power', 'PMIC_SDA': 'power',
                           'GND': 'soc'}
            records[ref] = g.Device(ref, net, 'TestPoint_Pad_D1.0mm',
                                    test_sheets[net], 0, 0, {'1': ('TEST', net)},
                                    note='Bare probe pad; no purchased or assembled part')
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
        if ref == 'SW6':
            names.update({'1': 'FEL_KEY_N', '2': 'FEL_KEY_N'})
        if ref == 'J3':
            names['7'] = 'FEL_KEY_N'
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
    s.child(root, 'text')[1] = s.Q('PCB connectivity reconstructed from the current candidate.\nPower targets are requirements, NOT measured/default outputs.\nRead POWER_REVIEW_CN.md before ordering PCBA.\nTF default ON: PH12 low or Hi-Z = ON; high = OFF.\nDisplay RESET = PA8; TE = PA9; both share the 1V8 domain.\nWake timer: approx 3 s nominal; measure 2.2-3.8 s.\nUSB routed as a pair; see USB_ROUTING_REPAIR_CN.md.\nUSB impedance / MIPI / display power still require validation.')
    all_libs = []
    for sheet, sheet_uuid in sheets.items():
        text = g.schematic_for_sheet(sheet, devices, g.uid('root-schematic'), sheet_uuid)
        if sheet == 'power':
            # Bring-up 0R links split PMIC-side and load-side rails; each side is
            # sourced physically by the PMIC through the fitted link.
            extra = []
            for idx, net in enumerate(EXTRA_SUPPLY_NETS):
                ref = f'#FLG{20 + idx}'; x = 254.0 + idx * 20.32; y = 279.4
                extra.append(f'(symbol (lib_id "Sameat:SUPPLY_SOURCE") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid "{g.uid(ref)}") (property "Reference" "{ref}" (at {x} {y-2.54} 0) (effects (font (size 1 1)) (hide yes))) (property "Value" "SUPPLY_SOURCE" (at {x} {y-5.08} 0) (effects (font (size 1 1)) (hide yes))) (instances (project "portable_display_epass" (path "/{g.uid('root-schematic')}/{sheet_uuid}" (reference "{ref}") (unit 1)))))')
                extra.append(f'(global_label "{net}" (shape passive) (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid "{g.uid(ref + "-label")}"))')
            text = text.replace('\t(embedded_fonts no)', '\n'.join(extra) + '\n\t(embedded_fonts no)', 1)
        tree = s.loads(text)
        # Native testpoints remain on-board/netlisted but are never BOM parts.
        for symbol in s.children(tree, 'symbol'):
            if s.props(symbol).get('Reference', '').startswith('TP'):
                s.setval(symbol, 'in_bom', 'no')
        for symbol in s.children(s.child(tree, 'lib_symbols'), 'symbol'):
            if str(symbol[1]).startswith('Sameat:TP'):
                s.setval(symbol, 'in_bom', 'no')
        selected = [d for d in devices if d.sheet == sheet]
        # Variable-height column packing prevents USB and SoC symbols overlapping.
        tops = [35.56] * 4
        top_margin = 5.08 if sheet == 'interfaces' else 6.35
        bottom_gap = 10.16 if sheet == 'interfaces' else 12.7
        objects = {s.val(x,'uuid'): x for x in tree if isinstance(x,list) and s.val(x,'uuid')}
        for d in sorted(selected, key=lambda d: -len(d.pins)):
            obj = objects[g.uid('symbol-'+d.ref)]
            half = max(5.08, (((len(d.pins)+1)//2)-1)*2.54/2+1.27)
            col = min(range(4), key=lambda c: tops[c])
            x = 63.5 + 132.08*col
            y = round((tops[col]+half+top_margin)/1.27)*1.27
            old = s.child(obj,'at')
            dx, dy = x-float(old[1]), y-float(old[2])
            translate(obj, dx, dy)
            for num in d.pins:
                for prefix in ['label','nc']:
                    label = objects.get(g.uid(f'{prefix}-{d.ref}-{num}'))
                    if label: translate(label, dx, dy)
            tops[col] = y+half+bottom_gap
        assert max(tops) < (347 if sheet == 'interfaces' else 365), (sheet,tops)
        # Supply flags certify only physical external feeds and inductor outputs.
        # They do not certify actual voltage, OTP state or load capability.
        for idx in range(6):
            for suffix in ['', '-label']:
                obj = objects.get(g.uid(f'#FLG{idx+1}'+suffix))
                if obj:
                    old = s.child(obj,'at')
                    translate(obj, 50.8+idx*76.2-float(old[1]), 381-float(old[2]))
        if sheet == 'interfaces':
            tree.append(['text', s.Q('USB ESD: U9 I/O2 pins 3/4 = DP; I/O1 pins 1/6 = DM. USB polarity at U2/J1 is unchanged.\nMain pair on F.Cu; the duplicated Type-C B7 contact uses a short B.Cu branch.\n90-ohm impedance and both-orientation HS/ESD tests remain pending. See USB_ROUTING_REPAIR_CN.md.'),
                         ['at', '38.1', '345.44', '0'],
                         ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left']],
                         ['uuid', s.Q(g.uid('usb-routing-note'))]])
            tree.append(['text', s.Q('TF POWER: R20 10k to GND; R21 100R. PH12 / SD_PWR_EN: LOW or Hi-Z = ON, HIGH = OFF.\n3V3 must be valid before boot. Card detection / cold-start waveforms still require hardware validation.'),
                         ['at', '38.1', '370.84', '0'],
                         ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left']],
                         ['uuid', s.Q(g.uid('tf-default-on-note'))]])
        if sheet == 'sensors':
            tree.append(['text', s.Q('WAKE DOMAINS: R17/R18 pull up to RTC_3V3. U11 SN74LVC2G17 isolates both IRQs from U2.\nU11/C52 use switched 3V3. RTC_INT_SOC_N -> PE7; ACCEL_INT_SOC_N -> PE6; polarity unchanged.\nRequire latched active-low IRQs and AON supply retention. See WAKE_DOMAIN_REPAIR_CN.md.'),
                         ['at', '38.1', '358.14', '0'],
                         ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left']],
                         ['uuid', s.Q(g.uid('wake-domain-note'))]])
            tree.append(['text', s.Q('WAKE TIMER: R12 910k 1%; C23 3.3uF 25V X7R 10% 0805; approx 3 s nominal.\nMeasure PWRON_N LOW for 2.2-3.8 s. RC tolerances alone do NOT guarantee this window.\nUse latched active-low interrupts; repeated edges retrigger U6. See WAKE_PULSE_REPAIR_CN.md.'),
                         ['at', '38.1', '370.84', '0'],
                         ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left']],
                         ['uuid', s.Q(g.uid('wake-timer-note'))]])
        if sheet == 'soc':
            tree.append(['text', s.Q('RECOVERY: hold SW6 before cold power-on. SW6 / J3.7 -> R33 1k -> PC1 / U2.56 (FEL_N).\nR34 10k pulls FEL_N to switched 3V3. BOOT_SEL[1:0] remains 11 on PC3 / PC2.\nJ3.7: open-drain LOW or release only. BROM tries UART upgrade before USB. See FEL_REPAIR_CN.md.'),
                         ['at', '38.1', '358.14', '0'],
                         ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left']],
                         ['uuid', s.Q(g.uid('fel-recovery-note'))]])
        if sheet in {'interfaces', 'soc'}:
            tree.append(['text', s.Q('DISPLAY GPIO: PA8 (U2.66) -> LCD_RST; PA9 / EINT9 (U2.65) <- LCD_TE. Both use 1V8.\nR32 10k holds reset LOW at boot. R29 must remain fitted 0R; VDDIO must share the PA supply.\nUpdate firmware pin assignments; PD19 / PD20 are now unconnected. See DISPLAY_IO_REPAIR_CN.md.'),
                         ['at', '38.1', '358.14' if sheet == 'interfaces' else '370.84', '0'],
                         ['effects', ['font', ['size', '1.27', '1.27']], ['justify', 'left']],
                         ['uuid', s.Q(g.uid('display-io-note-' + sheet))]])
        all_libs += [copy.deepcopy(x) for x in s.children(s.child(tree,'lib_symbols'),'symbol')]
        for title in [s.child(tree,'title_block')]:
            s.child(title,'date')[1] = s.Q(DATE)
            s.child(title,'rev')[1] = s.Q('FEL1')
            for comment in s.children(title,'comment'):
                if comment[1] == '1': comment[2] = s.Q('Current PCB pin nets; C3036461 factory configuration NOT verified')
        replace_atoms(tree, 'portable_display_epass', STEM)
        filename = {'power':'01_power','soc':'02_soc_v851s','sensors':'03_sensors','interfaces':'04_interfaces'}[sheet]
        s.dump(tree, BASE / f'{filename}.kicad_sch')
    replace_atoms(root, 'portable_display_epass', STEM)
    s.child(s.child(root,'title_block'),'date')[1] = s.Q(DATE)
    s.child(s.child(root,'title_block'),'rev')[1] = s.Q('FEL1')
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
