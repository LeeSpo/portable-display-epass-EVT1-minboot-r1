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


def check_package(board_path):
    import kicad_sexpr as s
    package = BASE/'verification/production_20261015'
    with (package/'BOM_JLC.csv').open(newline='') as stream:
        bom = list(csv.DictReader(stream))
    with (package/'CPL_JLC.csv').open(newline='') as stream:
        cpl = list(csv.DictReader(stream))
    bom_refs = [ref.strip() for row in bom for ref in row['Designator'].split(',')]
    cpl_refs = [row['Designator'] for row in cpl]
    fitted = {
        s.props(fp)['Reference']
        for fp in s.children(s.load(board_path), 'footprint')
        if 'dnp' not in s.values(fp, 'attr')
        and 'exclude_from_pos_files' not in s.values(fp, 'attr')
        and s.props(fp)['Reference'] != 'J3'  # Bare debug pogo pads, documented in the package README.
        and any(pad[1] for pad in s.children(fp, 'pad'))
    }
    problems = []
    if len(set(bom_refs)) != len(bom_refs) or len(set(cpl_refs)) != len(cpl_refs):
        problems.append('Duplicate BOM or CPL designator')
    if set(bom_refs) != set(cpl_refs) or set(cpl_refs) != fitted:
        problems.append(f'BOM/CPL/PCB sets differ: BOM-only {sorted(set(bom_refs)-set(cpl_refs))}; '
                        f'CPL-only {sorted(set(cpl_refs)-fitted)}; PCB-only {sorted(fitted-set(cpl_refs))}')
    if any(not row['LCSC Part #'].strip() for row in bom):
        problems.append('Missing BOM LCSC part number')
    if any(int(row['Quantity']) != len(row['Designator'].split(',')) for row in bom):
        problems.append('BOM quantity differs from designator count')
    for name in ['power_contract', 'fel_recovery', 'usb_routing', 'wake_domain']:
        report = json.loads((package/'checks'/f'{name}.json').read_text())
        if report['board_sha256'] != sha256(board_path) or not report['static_checks_passed']:
            problems.append(f'Production package {name} does not match this source board')
    return {
        'static_checks_passed': not problems,
        'board_sha256': sha256(board_path),
        'bom_rows': len(bom), 'placed_components': len(cpl_refs),
        'sides': dict(Counter(row['Layer'] for row in cpl)),
        'package_hashes': {str(p.relative_to(package)): sha256(p) for p in sorted(package.rglob('*')) if p.is_file()},
        'problems': problems, 'fabrication_released': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New or empty report directory')
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
                         'check_wake_domain', 'test_wake_domain']:
                report_name = name.removeprefix('check_') if name != 'test_wake_domain' else 'negative_checks'
                command = [sys.executable, str(project/'tools'/f'{name}.py'), '--output', str(output/f'{report_name}.json')]
                if name == 'check_power_contract':
                    command += ['--reports', str(output)]
                run(name, command)
            package = check_package(board)
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
