#!/usr/bin/env python3
"""Legacy name retained as a read-only compatibility entrypoint.

Automatic XML-to-pad relabeling is retired. Review design/pin_contract.json,
edit deliberately, and run source/PCB/schematic checks instead.
"""
from static_verify import run
import json
if __name__=='__main__':
    r=run();print('READ ONLY: no pads, copper, identities or coordinates were changed.')
    print(json.dumps({'static_checks_passed':r['static_checks_passed'],'problems':r['problems']},indent=2))
    raise SystemExit(0 if r['static_checks_passed'] else 1)
