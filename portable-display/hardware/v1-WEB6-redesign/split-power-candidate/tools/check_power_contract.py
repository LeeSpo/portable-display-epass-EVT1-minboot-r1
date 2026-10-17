#!/usr/bin/env python3
"""Check independent power pin requirements and native schematic/PCB parity.

Pass means static connectivity only. No available input proves factory OTP,
waveforms, current/thermal margins or that this board is ready to power up.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
import kicad_sexpr as s


def inspect(board_path, netlist_path, report_dir):
    requirements = json.loads((BASE/'power_requirements.json').read_text())
    board = s.load(board_path)
    actual = {}
    electrical = set()
    fitted_values = {}
    populated = set()
    component_properties = {}
    problems = []
    for fp in s.children(board,'footprint'):
        ref = s.props(fp)['Reference']
        fitted_values[ref] = s.props(fp).get('Value', '')
        component_properties[ref] = {**s.props(fp), 'Footprint': str(fp[1])}
        if 'dnp' not in s.values(fp, 'attr'):
            populated.add(ref)
        for pad in s.children(fp,'pad'):
            if not pad[1]: continue
            electrical.add(ref)
            net = s.child(pad,'net')
            name = str(net[-1]) if net else ''
            key = f'{ref}.{pad[1]}'
            name = 'NC' if not name or name.startswith('unconnected-') else name
            if key in actual and actual[key] != name:
                problems.append(f'Duplicate pad with conflicting nets: {key}')
            actual[key] = name
    for ref, pins in requirements['expected_pins'].items():
        for pin, net in pins.items():
            if actual.get(f'{ref}.{pin}') != net:
                problems.append(f'Power contract {ref}.{pin}: expected {net}, got {actual.get(f"{ref}.{pin}")}')
    for ref, value in requirements.get('expected_values', {}).items():
        if fitted_values.get(ref) != value:
            problems.append(f'Value contract {ref}: expected {value}, got {fitted_values.get(ref)}')
    for ref in requirements.get('required_fitted', []):
        if ref not in populated:
            problems.append(f'Population contract: {ref} must be fitted')
    for ref, expected in requirements.get('expected_component_properties', {}).items():
        for name, value in expected.items():
            actual_property = component_properties.get(ref, {}).get(name)
            if actual_property != value:
                problems.append(f'Component contract {ref}.{name}: expected {value}, got {actual_property}')
    xml = ET.parse(netlist_path).getroot()
    xml_values = {c.attrib['ref']: c.findtext('value') for c in xml.findall('./components/comp')}
    for ref, value in fitted_values.items():
        if ref in electrical and xml_values.get(ref) != value:
            problems.append(f'Schematic value mismatch {ref}: PCB={value}, schematic={xml_values.get(ref)}')
    refs = {c.attrib['ref'] for c in xml.findall('./components/comp') if not c.attrib['ref'].startswith('#')}
    if refs != electrical:
        problems.append(f'Component sets differ: PCB-only {sorted(electrical-refs)}; schematic-only {sorted(refs-electrical)}')
    schematic = {}
    for net in xml.findall('./nets/net'):
        name = net.attrib['name']
        name = 'NC' if name.startswith('unconnected-') else name
        for node in net.findall('node'):
            if node.attrib['ref'].startswith('#'): continue
            key = f'{node.attrib["ref"]}.{node.attrib["pin"]}'
            if key in schematic: problems.append(f'Duplicate schematic pin: {key}')
            schematic[key] = name
    for key, net in actual.items():
        if schematic.get(key, 'NC') != net:
            problems.append(f'Schematic mismatch {key}: PCB={net}, schematic={schematic.get(key)}')
    for key in schematic.keys()-actual.keys(): problems.append(f'Extra schematic pin {key}')
    native = {}
    for filename in ['erc.json','drc.json']:
        data = json.loads((report_dir/filename).read_text())
        for field in ['date','source','kicad_version']:
            if not data.get(field): problems.append(f'{filename}: missing {field}')
        if filename == 'erc.json':
            assert isinstance(data.get('sheets'),list) and data['sheets'], 'Missing ERC sheets'
            entries = [v for sh in data['sheets'] for v in sh['violations']]
        else:
            assert all(isinstance(data.get(k),list) for k in ['violations','unconnected_items','schematic_parity'])
            entries = sum([data[k] for k in ['violations','unconnected_items','schematic_parity']],[])
        native[filename] = len(entries)
        problems += [f'{filename}: {v.get("description",v)}' for v in entries]
    return {
        'static_checks_passed': not problems,
        'board_sha256': hashlib.sha256(board_path.read_bytes()).hexdigest(),
        'electrical_components': len(electrical),
        'unique_numbered_pads': len(actual),
        'power_pins_checked': sum(len(v) for v in requirements['expected_pins'].values()),
        'component_values_checked': len(electrical),
        'independent_value_requirements': requirements.get('expected_values', {}),
        'required_fitted': requirements.get('required_fitted', []),
        'native_findings': native,
        'problems': problems,
        'factory_configuration_verified': False,
        'cold_start_verified': False,
        'fabrication_released': False,
        'remaining_blocker': 'C3036461 factory voltage/enable/sequence not specified by available platform information; no physical measurements',
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--board',type=Path,default=BASE/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb')
    p.add_argument('--reports',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    result = inspect(args.board,args.reports/'netlist.xml',args.reports)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(result,indent=2,ensure_ascii=False))
    raise SystemExit(0 if result['static_checks_passed'] else 1)
