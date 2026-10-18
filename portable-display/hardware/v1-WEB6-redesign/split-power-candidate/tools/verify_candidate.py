#!/usr/bin/env python3
"""Verify an isolated candidate copy without saving changes to hardware sources.

The saved-fill DRC is diagnostic. Acceptance uses native zone refill, all
configured severities and schematic parity, without changing project rules.
This verifies engineering records, not manufacturing release or operation.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parents[1]
STEM = 'ak_display_38x64_SPLIT_POWER_CANDIDATE'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = [p for p in BASE.glob('*.kicad_*') if p.suffix in
             {'.kicad_pcb', '.kicad_sch', '.kicad_pro', '.kicad_sym'}]
    paths += list((BASE/'sameat.pretty').glob('*.kicad_mod'))
    paths += list((BASE/'tools').glob('*.py'))
    paths += [BASE/name for name in ['fp-lib-table', 'sym-lib-table', 'power_requirements.json', 'requirements.txt']]
    return {str(p.relative_to(BASE)): sha256(p) for p in sorted(paths)}


def find_package(verification=None):
    """Require an unambiguous retained preview rather than silently picking a date."""
    verification = verification or BASE/'verification'
    packages = sorted(path for path in verification.glob('production_*') if path.is_dir())
    if len(packages) != 1:
        raise RuntimeError('Expected exactly one retained production package; '
                           'select the intended package with --package PATH '
                           f'(found {len(packages)})')
    return packages[0]


def read_assembly_csv(path, fields):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if not set(fields).issubset(headers) or len(headers) != len(set(headers)):
            raise ValueError(f'{path.name}: missing or duplicate required CSV headers')
        rows = list(reader)
    if any(None in row or any(row[field] is None for field in fields) for row in rows):
        raise ValueError(f'{path.name}: CSV row has missing or extra cells')
    return rows


def check_package(board_path, package=None):
    import kicad_sexpr as s
    package = (Path(package) if package is not None else find_package()).resolve()
    bom = read_assembly_csv(package/'BOM_JLC.csv',
                            ['Comment', 'Designator', 'Footprint', 'LCSC Part #', 'Quantity'])
    cpl = read_assembly_csv(package/'CPL_JLC.csv',
                            ['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    bom_refs = [ref.strip() for row in bom for ref in row['Designator'].split(',')]
    cpl_refs = [row['Designator'].strip() for row in cpl]
    problems = []
    fitted = {}
    for fp in s.children(s.load(board_path), 'footprint'):
        ref = s.props(fp)['Reference']
        attrs = set(s.values(fp, 'attr'))
        if 'dnp' in attrs or ref == 'J3' or not any(pad[1] for pad in s.children(fp, 'pad')):
            # Legacy J3 is the bare debug pogo footprint documented in the README.
            continue
        excluded_bom = 'exclude_from_bom' in attrs
        excluded_pos = 'exclude_from_pos_files' in attrs
        if excluded_bom != excluded_pos:
            problems.append(f'PCB {ref} must be excluded from both BOM and position files, or neither')
        if excluded_bom or excluded_pos:
            continue
        if ref in fitted:
            problems.append(f'Duplicate PCB designator {ref}')
        fitted[ref] = fp
    if len(set(bom_refs)) != len(bom_refs) or len(set(cpl_refs)) != len(cpl_refs):
        problems.append('Duplicate BOM or CPL designator')
    if set(bom_refs) != set(cpl_refs) or set(cpl_refs) != set(fitted):
        problems.append(f'BOM/CPL/PCB sets differ: BOM-only {sorted(set(bom_refs)-set(cpl_refs))}; '
                        f'CPL-only {sorted(set(cpl_refs)-set(fitted))}; PCB-only {sorted(set(fitted)-set(cpl_refs))}')
    for row in bom:
        refs = [ref.strip() for ref in row['Designator'].split(',')]
        lcsc = row['LCSC Part #'].strip()
        if not lcsc:
            problems.append('Missing BOM LCSC part number')
        try:
            if int(row['Quantity']) != len(refs):
                problems.append('BOM quantity differs from designator count')
        except ValueError:
            problems.append('Invalid BOM quantity')
        # A row is an assembly group: every member must have these same board
        # attributes. A valid-looking part number alone does not establish parity.
        for ref in refs:
            if ref not in fitted:
                continue
            fp = fitted[ref]
            props = s.props(fp)
            expected = (props.get('Value', ''), str(fp[1]).split(':')[-1], props.get('LCSC', '').strip())
            actual = (row['Comment'].strip(), row['Footprint'].strip(), lcsc)
            if not expected[2] or actual != expected:
                problems.append(f'BOM {ref} Value/Footprint/LCSC differs from PCB: '
                                f'{actual!r} != {expected!r}')
    for row in cpl:
        ref = row['Designator'].strip()
        if ref not in fitted:
            continue
        fp = fitted[ref]
        at = s.values(fp, 'at')
        layer = {'F.Cu': 'Top', 'B.Cu': 'Bottom'}.get(s.val(fp, 'layer'))
        if row['Layer'].strip() != layer:
            problems.append(f'CPL {ref} layer differs from PCB')
        try:
            # The retained package uses native KiCad absolute coordinates (mm),
            # negated Y and raw footprint rotation, including on the bottom side.
            # Do not subtract aux_axis_origin or mirror bottom rotations here.
            x, y = [float(row[key].strip().removesuffix('mm')) for key in ['Mid X', 'Mid Y']]
            rotation = float(row['Rotation'])
            if not all(math.isfinite(value) for value in [x, y, rotation]):
                raise ValueError('non-finite placement')
            if abs(x-float(at[0])) > 0.000001 or abs(y+float(at[1])) > 0.000001:
                problems.append(f'CPL {ref} coordinates differ from PCB')
            angle = float(at[2]) if len(at) > 2 else 0.0
            if abs((rotation-angle+180) % 360-180) > 0.000001:
                problems.append(f'CPL {ref} rotation differs from PCB')
        except ValueError:
            problems.append(f'Invalid CPL {ref} coordinates or rotation')
    for name in ['power_contract', 'fel_recovery', 'usb_routing', 'wake_domain']:
        report = json.loads((package/'checks'/f'{name}.json').read_text())
        if report['board_sha256'] != sha256(board_path) or report['static_checks_passed'] is not True:
            problems.append(f'Production package {name} does not match this source board')
    return {
        'static_checks_passed': not problems,
        'board_sha256': sha256(board_path), 'package_path': str(package),
        'bom_rows': len(bom), 'placed_components': len(cpl_refs),
        'sides': dict(Counter(row['Layer'] for row in cpl)),
        'package_hashes': {str(p.relative_to(package)): sha256(p) for p in sorted(package.rglob('*')) if p.is_file()},
        'problems': problems, 'fabrication_released': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New or empty report directory')
    parser.add_argument('--package', type=Path,
                        help='Production preview directory; default requires one retained verification/production_*')
    parser.add_argument('--kicad-cli', default=os.environ.get('KICAD_CLI') or shutil.which('kicad-cli')
                        or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error('--output must be empty to avoid mixing evidence from different runs')
    output.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    provenance = {
        'date_utc': datetime.now(timezone.utc).isoformat(),
        'source_hashes': before, 'native_zone_refill': True,
        'source_files_modified': False, 'fabrication_released': False,
        'hardware_verified': False, 'commands': [], 'checks_passed': False,
    }
    try:
        version = subprocess.check_output([args.kicad_cli, 'version'], text=True).strip()
        provenance['kicad_version'] = version
        with tempfile.TemporaryDirectory(prefix='verify-candidate-') as temp:
            project = Path(temp)/'project'
            shutil.copytree(BASE, project, ignore=shutil.ignore_patterns(
                'verification', '.venv', '.history', '__pycache__', '.DS_Store', '*.kicad_prl'))
            board = project/f'{STEM}.kicad_pcb'
            schematic = project/f'{STEM}.kicad_sch'

            def run(name, command, required=True):
                result = subprocess.run(command, text=True, capture_output=True, cwd=project)
                (output/f'{name}.log').write_text(result.stdout + result.stderr)
                normalized = [str(v).replace(str(project), '<isolated-project>')
                              .replace(str(output), '<reports>') for v in command]
                provenance['commands'].append({'name': name, 'argv': normalized, 'exit_code': result.returncode})
                print(f'{name}: exit {result.returncode}', flush=True)
                if required and result.returncode:
                    raise RuntimeError(f'{name} failed; see {output/name}.log')

            common = ['--format', 'json', '--severity-all', '--exit-code-violations']
            run('erc', [args.kicad_cli, 'sch', 'erc', *common, '-o', str(output/'erc.json'), str(schematic)])
            run('saved_fill_drc', [args.kicad_cli, 'pcb', 'drc', *common, '--schematic-parity',
                                   '-o', str(output/'saved_fill_drc.json'), str(board)], required=False)
            run('drc', [args.kicad_cli, 'pcb', 'drc', *common, '--schematic-parity', '--refill-zones',
                        '-o', str(output/'drc.json'), str(board)])
            run('netlist', [args.kicad_cli, 'sch', 'export', 'netlist', '--format', 'kicadxml',
                            '-o', str(output/'netlist.xml'), str(schematic)])
            for name in ['check_power_contract', 'check_fel_recovery', 'check_usb_routing',
                         'check_wake_domain', 'test_wake_domain', 'test_package_integrity']:
                report_name = {'test_wake_domain': 'negative_checks',
                               'test_package_integrity': 'package_negative_checks'}.get(
                                   name, name.removeprefix('check_'))
                command = [sys.executable, str(project/'tools'/f'{name}.py'), '--output', str(output/f'{report_name}.json')]
                if name == 'check_power_contract':
                    command += ['--reports', str(output)]
                run(name, command)
            package = check_package(board, args.package)
            (output/'package_integrity.json').write_text(json.dumps(package, indent=2)+'\n')
            if not package['static_checks_passed']:
                raise RuntimeError(f'Package integrity: {package["problems"]}')
            saved = json.loads((output/'saved_fill_drc.json').read_text())
            provenance['saved_fill_findings'] = {key: len(saved[key]) for key in
                                                 ['violations', 'unconnected_items', 'schematic_parity']}
            provenance['checks_passed'] = True
    except (OSError, subprocess.SubprocessError, RuntimeError, KeyError, ValueError) as error:
        provenance['error'] = str(error)
    finally:
        provenance['source_files_modified'] = source_hashes() != before
        if provenance['source_files_modified']:
            provenance['checks_passed'] = False
        (output/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    print(json.dumps({key: provenance.get(key) for key in ['checks_passed', 'source_files_modified', 'error']}, indent=2))
    return 0 if provenance['checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
