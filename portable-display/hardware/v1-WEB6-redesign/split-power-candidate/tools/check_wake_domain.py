#!/usr/bin/env python3
"""Check wake-domain isolation independently of generated schematic pin tables.

Native DRC/ ERC and check_power_contract must also pass. This checks topology,
not simulated transistors, PMIC configuration or hardware waveforms.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE.parents[1] / 'v0_legacy' / 'tools'))
import kicad_sexpr as s


def inspect(path):
    board = s.load(path)
    parts = {s.props(f)['Reference']: f for f in s.children(board, 'footprint')}
    nets = {}
    for ref, fp in parts.items():
        for pad in s.children(fp, 'pad'):
            if pad[1]:
                name = s.values(pad, 'net')
                nets[f'{ref}.{pad[1]}'] = str(name[-1]) if name else ''
    errors = []
    def require(ok, reason):
        if not ok:
            errors.append(reason)
    def net(pin):
        require(pin in nets, f'Missing electrical pin {pin}')
        return nets.get(pin)
    def joined(pins):
        values = [net(pin) for pin in pins]
        return bool(values[0]) and len(set(values)) == 1
    def fitted(ref):
        return ref in parts and 'dnp' not in s.values(parts[ref], 'attr')
    aon, switched, ground = net('U1.28'), net('U2.22'), net('U1.41')
    require(len({aon, switched, ground}) == 3, 'Always-on, switched power and ground must be different nets')
    require(joined(['U11.5', 'C52.1', 'U2.22']), 'Buffer and bypass must use the SoC switched supply')
    require(joined(['U11.2', 'C52.2', 'U1.41']), 'Buffer and bypass ground missing')
    require(joined(['U1.28', 'U6.8', 'U4.2', 'U4.9', 'U5.7', 'R11.1', 'R17.1', 'R18.1']),
            'Wake sources, one-shot and all wake pull-ups must stay in the always-on domain')
    require(joined(['D2.2', 'D3.2', 'R11.2', 'U6.1']), 'Diode OR must feed the always-on one-shot')
    source_allow = [({'U5.2', 'D2.1', 'R17.2', 'U11.1'}, ['U11.6', 'U2.24']),
                    ({'U4.12', 'D3.1', 'R18.2', 'U11.3'}, ['U11.4', 'U2.30'])]
    for source_pins, output_pins in source_allow:
        source_pins = sorted(source_pins)
        require(joined(source_pins), f'Wake source path incomplete: {source_pins}')
        require(joined(output_pins), f'Buffered SoC path incomplete: {output_pins}')
        source_net, output_net = net(source_pins[0]), net(output_pins[0])
        require(source_net != output_net, 'Raw always-on IRQ must not directly drive the SoC')
        require({p for p, n in nets.items() if n == source_net} == set(source_pins),
                f'Unexpected load / direct cross-domain connection on {source_net}')
        require({p for p, n in nets.items() if n == output_net} == set(output_pins),
                f'Unexpected connection on buffered output {output_net}')
    for ref in ['U11', 'C52', 'R11', 'R17', 'R18', 'D2', 'D3', 'U6', 'Q1', 'Q2']:
        require(fitted(ref), f'{ref} must be populated')
    for ref in ['R11', 'R17', 'R18']:
        require(s.props(parts.get(ref, [])).get('Value') == '10k', f'{ref} must be 10k')
    require(s.props(parts.get('C52', [])).get('Value') == '100n', 'C52 must be 100n')
    p = s.props(parts.get('U11', []))
    require(p.get('MPN') == 'SN74LVC2G17DBVR' and p.get('LCSC') == 'C10429',
            'Isolation requires the qualified TI SN74LVC2G17DBVR / C10429, not an unspecified substitute')
    require(str(parts.get('U11', ['', ''])[1]) == 'Sameat:SN74LVC2G17_DBV6',
            'Isolation buffer footprint must match DBV6 pin mapping')
    # Original off-state fault: 10k to AON and two 10k branches to dead 3V3.
    # Ideal constant-drop diode model, no additional SoC clamp current.
    old_high = [(3.3 + 2 * vf) / 3 for vf in [.2, .4]]
    return {
        'static_checks_passed': not errors,
        'board_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'errors': errors,
        'old_off_state_model': {'assumptions': 'RTC_3V3=3.3V; 3V3=0V; equal 10k resistors; diode Vf=0.2..0.4V; sources released',
                                'wake_req_v': old_high, 'u6_vih_min_v_at_3_to_3_6_v': 2.0},
        'new_domain': {'source_pullups': 'RTC_3V3', 'soc_buffer_supply': '3V3',
                       'input_voltage_allowed_at_vcc_zero': True,
                       'ti_input_leakage_bound_a': 5e-6, 'ti_i_off_bound_a': 1e-5,
                       'drop_from_5ua_buffer_input_leakage_across_10k_v': .05,
                       'leakage_note': 'TI test conditions apply; excludes sensor/diode leakage and PCB contamination'},
        'hardware_verified': False,
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--board', type=Path, default=BASE/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = inspect(args.board)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result['static_checks_passed'] else 1)
