#!/usr/bin/env python3
"""Apply reviewed WEB6 placement plan using KiCad's native PCB model.

Run with the Python bundled with KiCad. Input and output must be explicit.
Removes copper on moved non-ground nets for rerouting; never changes pad nets.
"""
import argparse
import json
from pathlib import Path
import pcbnew


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input')
    ap.add_argument('output')
    ap.add_argument('plan')
    args = ap.parse_args()
    board = pcbnew.LoadBoard(args.input)
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    assert not {'U3', 'C22', 'R7', 'R8', 'R9'} & set(fps), 'Use NAND-removed baseline'
    plan = json.loads(Path(args.plan).read_text())['moves']
    before = {r: {p.GetNumber(): p.GetNetname() for p in f.Pads()} for r, f in fps.items()}
    affected = {p.GetNetname() for r in plan for p in fps[r].Pads()
                if p.GetNetname() and p.GetNetname() != 'GND'}
    removed = 0
    for r, (x, y, a) in plan.items():
        f = fps[r]
        f.SetOrientationDegrees(a)
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    after = {r: {p.GetNumber(): p.GetNetname() for p in f.Pads()} for r, f in fps.items()}
    assert before == after
    pcbnew.SaveBoard(args.output, board)
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'v0_legacy/tools'))
    from kicad_sexpr import load, dumps, values
    tree = load(args.output)
    kept = []
    for node in tree:
        if isinstance(node, list) and node and node[0] in ('segment', 'via') and str(values(node, 'net')[-1]) in affected:
            removed += 1
        else:
            kept.append(node)
    Path(args.output).write_text(dumps(kept) + '\n')
    print(json.dumps({'moved': len(plan), 'removed_copper': removed,
                      'affected_nets': sorted(affected), 'pad_nets_preserved': True}))


if __name__ == '__main__':
    main()
