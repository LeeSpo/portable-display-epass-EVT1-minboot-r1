#!/usr/bin/env python3
"""Reject stale or mismatched assembly exports using isolated synthetic fixtures."""
import argparse
import copy
import csv
import json
from pathlib import Path
import tempfile

import kicad_sexpr as s
from verify_candidate import check_package, find_package, sha256


BOM_FIELDS = ['Comment', 'Designator', 'Footprint', 'LCSC Part #', 'Quantity']
CPL_FIELDS = ['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation']


def write_csv(path, fields, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    records = []
    with tempfile.TemporaryDirectory(prefix='package-integrity-fault-') as temp:
        root = Path(temp)
        board_path = root/'fixture.kicad_pcb'
        board = s.loads('''(kicad_pcb
            (setup (aux_axis_origin 10 20))
            (footprint "Sameat:0402" (layer "F.Cu") (at 1.25 2.5 90)
                (property "Reference" "C1") (property "Value" "100n")
                (property "LCSC" "C1525") (attr smd) (pad "1" smd rect))
            (footprint "Sameat:0402" (layer "F.Cu") (at 3 4)
                (property "Reference" "C2") (property "Value" "100n")
                (property "LCSC" "C1525") (attr smd) (pad "1" smd rect))
            (footprint "Sameat:QFN" (layer "B.Cu") (at 5 6 -90)
                (property "Reference" "U1") (property "Value" "PMIC")
                (property "LCSC" "C12345") (attr smd) (pad "1" smd rect))
            (footprint "TestPoint:Pad" (layer "F.Cu") (at 7 8)
                (property "Reference" "TP1")
                (attr exclude_from_bom exclude_from_pos_files) (pad "1" smd circle))
            (footprint "Sameat:HDR8" (layer "F.Cu") (at 9 10)
                (property "Reference" "J3") (attr through_hole) (pad "1" thru_hole circle))
            (footprint "Sameat:0402" (layer "F.Cu") (at 11 12)
                (property "Reference" "R31") (attr smd dnp) (pad "1" smd rect)))''')
        bom = [dict(zip(BOM_FIELDS, row)) for row in [
            ['100n', 'C1,C2', '0402', 'C1525', '2'],
            ['PMIC', 'U1', 'QFN', 'C12345', '1'],
        ]]
        cpl = [dict(zip(CPL_FIELDS, row)) for row in [
            ['C1', '1.250000mm', '-2.500000mm', 'Top', '90'],
            ['C2', '3mm', '-4mm', 'Top', '0'],
            ['U1', '5mm', '-6mm', 'Bottom', '-90'],
        ]]
        package = root/'production_20990101'
        (package/'checks').mkdir(parents=True)

        def inspect_case(title, expected=None, change=None, change_files=None):
            case_board, case_bom, case_cpl = copy.deepcopy((board, bom, cpl))
            if change:
                change(case_board, case_bom, case_cpl)
            s.dump(case_board, board_path)
            write_csv(package/'BOM_JLC.csv', BOM_FIELDS, case_bom)
            write_csv(package/'CPL_JLC.csv', CPL_FIELDS, case_cpl)
            for name in ['power_contract', 'fel_recovery', 'usb_routing', 'wake_domain']:
                report = {'board_sha256': sha256(board_path), 'static_checks_passed': True}
                if title == 'Stale source hash' and name == 'power_contract':
                    report['board_sha256'] = '0'*64
                if title == 'Failed source check' and name == 'power_contract':
                    report['static_checks_passed'] = False
                (package/'checks'/f'{name}.json').write_text(json.dumps(report))
            if change_files:
                change_files(package)
            try:
                result = check_package(board_path, package)
            except ValueError as error:
                result = {'static_checks_passed': False, 'problems': [str(error)]}
            passed = (result['static_checks_passed'] if expected is None else
                      not result['static_checks_passed'] and
                      any(expected in problem for problem in result['problems']))
            records.append({'case': title, 'passed': passed, 'problems': result['problems']})

        inspect_case('Baseline with excluded testpoint and nonzero aux origin')
        inspect_case('Equivalent angle', change=lambda b, m, c: c[2].update(Rotation='270'))
        inspect_case('Wrong CPL coordinate', 'coordinates differ',
                     lambda b, m, c: c[0].update({'Mid X': '1.35mm'}))
        inspect_case('Wrong CPL side', 'layer differs',
                     lambda b, m, c: c[2].update(Layer='Top'))
        inspect_case('Wrong CPL rotation', 'rotation differs',
                     lambda b, m, c: c[2].update(Rotation='90'))
        inspect_case('Non-finite CPL coordinate', 'Invalid CPL',
                     lambda b, m, c: c[0].update({'Mid X': 'nan'}))
        inspect_case('Wrong BOM LCSC', 'LCSC differs',
                     lambda b, m, c: m[0].update({'LCSC Part #': 'C999999'}))
        inspect_case('Missing BOM LCSC', 'Missing BOM LCSC',
                     lambda b, m, c: m[0].update({'LCSC Part #': ''}))
        inspect_case('Wrong BOM quantity', 'quantity differs',
                     lambda b, m, c: m[0].update(Quantity='3'))
        inspect_case('Invalid BOM quantity', 'Invalid BOM quantity',
                     lambda b, m, c: m[0].update(Quantity='two'))
        inspect_case('Wrong BOM footprint', 'LCSC differs',
                     lambda b, m, c: m[0].update(Footprint='0603'))

        def mixed_group(case_board, case_bom, case_cpl):
            props = s.children(s.children(case_board, 'footprint')[1], 'property')
            next(prop for prop in props if prop[1] == 'Value')[2] = s.Q('1u')

        inspect_case('Mixed BOM grouping', 'BOM C2', mixed_group)
        inspect_case('Duplicate designator', 'Duplicate BOM or CPL',
                     lambda b, m, c: c.append(copy.deepcopy(c[0])))
        inspect_case('Missing placement', 'sets differ', lambda b, m, c: c.pop())
        inspect_case('Stale source hash', 'does not match this source board')
        inspect_case('Failed source check', 'does not match this source board')
        inspect_case('Duplicate PCB designator', 'Duplicate PCB designator',
                     lambda b, m, c: b.append(copy.deepcopy(s.children(b, 'footprint')[0])))
        inspect_case('Testpoint excluded only from BOM', 'must be excluded from both',
                     lambda b, m, c: s.child(s.children(b, 'footprint')[3], 'attr').remove(
                         'exclude_from_pos_files'))
        inspect_case('Testpoint excluded only from positions', 'must be excluded from both',
                     lambda b, m, c: s.child(s.children(b, 'footprint')[3], 'attr').remove(
                         'exclude_from_bom'))
        inspect_case('Excluded testpoint erroneously placed', 'sets differ',
                     lambda b, m, c: c.append(dict(zip(CPL_FIELDS,
                         ['TP1', '7mm', '-8mm', 'Top', '0']))))
        inspect_case('Missing BOM CSV header', 'required CSV headers', change_files=lambda p:
                     (p/'BOM_JLC.csv').write_text('Comment,Designator\n100n,C1\n'))
        inspect_case('Short CPL CSV row', 'missing or extra cells', change_files=lambda p:
                     (p/'CPL_JLC.csv').write_text(','.join(CPL_FIELDS)+'\nC1,1.25mm,-2.5mm,Top\n'))

        for count in [0, 1, 2]:
            verification = root/f'discovery_{count}'
            verification.mkdir()
            for index in range(count):
                (verification/f'production_{20990101+index}').mkdir()
            try:
                selected = find_package(verification)
                passed = count == 1 and selected.name == 'production_20990101'
            except RuntimeError:
                passed = count != 1
            records.append({'case': f'Discovery with {count} retained packages', 'passed': passed})

    report = {'all_cases_passed': all(record['passed'] for record in records), 'cases': records}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    return 0 if report['all_cases_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
