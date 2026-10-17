#!/usr/bin/env python3
"""Independent PC1 FEL topology and static DC margins, not a BROM hardware test.

Sources: Allwinner V851S-PER2 V1.2 sheet 8 and V851S/V851SE v0.1,
Table 2-7 / section 3.5. Native ERC/DRC and schematic parity are also required.
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
    pins = {}
    for ref, fp in parts.items():
        for pad in s.children(fp, 'pad'):
            if pad[1]:
                net = s.values(pad, 'net')
                pins[f'{ref}.{pad[1]}'] = str(net[-1]) if net else ''
    errors = []
    def require(ok, message):
        if not ok:
            errors.append(message)
    def group(expected, name):
        nets = [pins.get(pin, '') for pin in expected]
        require(bool(nets[0]) and not nets[0].startswith('unconnected-')
                and len(set(nets)) == 1, f'{name}: required pins disconnected')
        require({p for p, n in pins.items() if n == nets[0]} == set(expected),
                f'{name}: unexpected load or wrong CPU pin')
        return nets[0]
    fel = group(['U2.56', 'R33.2', 'R34.2'], 'PC1 FEL input')
    key = group(['R33.1', 'SW6.1', 'SW6.2', 'J3.7'], 'Recovery key / pogo')
    boot0 = group(['U2.59', 'R10.2'], 'PC2 BOOT0 strap')
    boot1 = group(['U2.58', 'R28.2'], 'PC3 BOOT1 strap')
    supply, ground = pins.get('U2.55'), pins.get('U2.89')
    require(len({fel, key, boot0, boot1, supply, ground}) == 6,
            'FEL, key, boot straps, switched supply and ground must stay distinct')
    require(all(pins.get(p) == supply for p in ['R10.1', 'R28.1', 'R34.1']),
            'All recovery and boot pull-ups must use switched VCC-PC')
    require(pins.get('SW6.3') == ground and pins.get('J3.1') == ground,
            'Switch and debugger ground missing')
    for ref, value in {'R10': '10k', 'R28': '10k', 'R33': '1k', 'R34': '10k'}.items():
        require(s.props(parts.get(ref, [])).get('Value') == value,
                f'{ref} must be {value}; recalculate DC margins for other values')
    for ref in ['R10', 'R28', 'R33', 'R34', 'SW6', 'J3']:
        require(ref in parts and 'dnp' not in s.values(parts[ref], 'attr'), f'{ref} must be populated')
    for ref, mpn, lcsc in [('R33', '0402WGF1001TCE', 'C11702'), ('R34', '0402WGF1002TCE', 'C25744')]:
        prop = s.props(parts.get(ref, []))
        require(prop.get('MPN') == mpn and prop.get('LCSC') == lcsc,
                f'{ref} must retain the qualified 1% resistor part')
        require(str(parts.get(ref, ['', ''])[1]) == 'Sameat:0402', f'{ref} footprint must be 0402')
    # Released: conservatively ignore internal pull-up and allow 20 uA total
    # sink leakage at CPU + fixture. Pressed: strongest internal 12k pull-up,
    # external 10k -1%, series 1k +1%, 10 ohm key/contact and 10 uA source leakage.
    # Compare each voltage with its own supply-scaled threshold.
    corners = []
    for vdd in [2.97, 3.63]:
        r_up = 1 / (1 / 9900 + 1 / 12000)
        r_down = 1010 + 10
        low = (vdd / r_up + 10e-6) / (1 / r_up + 1 / r_down)
        high = vdd - 20e-6 * 10100
        corners.append({'vdd_v': vdd, 'pressed_max_v': low, 'vil_max_v': .3*vdd,
                        'low_margin_v': .3*vdd-low, 'released_min_v': high,
                        'vih_min_v': .7*vdd, 'high_margin_v': high-.7*vdd})
    require(all(c['low_margin_v'] > 0 and c['high_margin_v'] > 0 for c in corners),
            'Recovery input DC logic margin missing')
    return {'static_checks_passed': not errors, 'errors': errors,
            'board_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'physical_cpu_pin': 'U2.56 / PC1 / SPI0-CS0',
            'default_boot_sel': '11 (PC3/PC2); independent of recovery key',
            'dc_assumptions': {'resistor_tolerance': .01, 'internal_pullup_min_ohm': 12000,
                               'contact_max_ohm': 10, 'pressed_source_leakage_a': 10e-6,
                               'released_total_sink_leakage_a': 20e-6,
                               'fixture': 'open-drain LOW or release; no external pull-up'},
            'dc_corners': corners,
            'accidental_gpio_high_key_current_upper_bound_a': 3.63 / 990,
            'hardware_verified': False, 'brom_enumeration_verified': False}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--board', type=Path, default=BASE/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = inspect(args.board)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result['static_checks_passed'] else 1)
