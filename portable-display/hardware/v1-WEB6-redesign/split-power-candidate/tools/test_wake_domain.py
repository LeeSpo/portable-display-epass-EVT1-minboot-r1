#!/usr/bin/env python3
"""Fault injection: the wake audit must reject plausible assembly/wiring regressions."""
import argparse
import copy
import json
from pathlib import Path
import tempfile
from check_wake_domain import BASE, inspect, s


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    board_path = BASE/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pcb'
    assert inspect(board_path)['static_checks_passed'], 'Current board fails baseline wake audit'
    board = s.load(board_path)
    cases = [
        ('RTC pull-up on dead rail', 'R17', '1', '3V3', 'always-on domain'),
        ('Accel pull-up on dead rail', 'R18', '1', '3V3', 'always-on domain'),
        ('SoC connected directly to raw IRQ', 'U2', '24', 'RTC_INT_N', 'directly drive'),
        ('Buffer powered by always-on rail', 'U11', '5', 'RTC_3V3', 'switched supply'),
        ('Unqualified replacement buffer', 'U11', 'MPN', '74HC2G17', 'qualified TI'),
        ('Unpopulated isolation buffer', 'U11', 'dnp', None, 'must be populated'),
    ]
    records = []
    with tempfile.TemporaryDirectory(prefix='wake-domain-fault-') as tmp:
        for title, ref, pin, value, expected in cases:
            b = copy.deepcopy(board)
            fp = next(f for f in s.children(b, 'footprint') if s.props(f)['Reference'] == ref)
            if pin == 'MPN':
                next(p for p in s.children(fp, 'property') if p[1] == pin)[2] = s.Q(value)
            elif pin == 'dnp':
                s.child(fp, 'attr').append('dnp')
            else:
                pad = next(p for p in s.children(fp, 'pad') if p[1] == pin)
                s.child(pad, 'net')[-1] = s.Q(value)
            path = Path(tmp)/'fault.kicad_pcb'
            s.dump(b, path)
            result = inspect(path)
            # A direct CPU connection must be rejected, whether the output net
            # itself was joined or just the CPU input was moved to the raw net.
            if pin == '24':
                expected = 'direct cross-domain'
            passed = not result['static_checks_passed'] and any(expected in e for e in result['errors'])
            records.append({'case': title, 'rejected_as_expected': passed, 'errors': result['errors']})
    report = {'all_faults_rejected': all(r['rejected_as_expected'] for r in records), 'cases': records}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    assert report['all_faults_rejected']


if __name__ == '__main__':
    main()
