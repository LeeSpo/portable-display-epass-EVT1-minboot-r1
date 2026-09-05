#!/usr/bin/env python3
"""Check U2-neighborhood via pitch on a KiCad PCB; estimate 0.50 pad clearance."""
from __future__ import annotations

import argparse
import math
import re
import statistics
import sys
from pathlib import Path


def find_u2(text: str):
    m = re.search(r'\(property\s+"Reference"\s+"U2"', text)
    if not m:
        raise SystemExit("U2 footprint not found")
    start = text.rfind("(footprint", 0, m.start())
    body = text[start : start + 80000]
    at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)", body)
    return float(at.group(1)), float(at.group(2)), body


def vias_near(text: str, ux: float, uy: float, radius: float):
    out = []
    for m in re.finditer(r"\(via\b(.*?)\n\t\)", text, re.S):
        b = m.group(1)
        am = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)\)", b)
        sm = re.search(r"\(size\s+([\d.]+)", b)
        dm = re.search(r"\(drill\s+([\d.]+)", b)
        if not am:
            continue
        x, y = float(am.group(1)), float(am.group(2))
        if math.hypot(x - ux, y - uy) <= radius:
            out.append(
                (
                    x,
                    y,
                    float(sm.group(1)) if sm else float("nan"),
                    float(dm.group(1)) if dm else float("nan"),
                )
            )
    return out


def pair_gaps(vias, pad: float):
    gaps = []
    for i, a in enumerate(vias):
        for b in vias[i + 1 :]:
            d = math.hypot(a[0] - b[0], a[1] - b[1])
            if d < 3.0:
                gaps.append(d - pad)
    return gaps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pcb", type=Path)
    ap.add_argument("--radius", type=float, default=12.0)
    ap.add_argument("--target-pad", type=float, default=0.50)
    ap.add_argument("--min-gap", type=float, default=0.15)
    args = ap.parse_args()
    text = args.pcb.read_text(errors="ignore")
    ux, uy, _ = find_u2(text)
    vias = vias_near(text, ux, uy, args.radius)
    if not vias:
        print("no vias near U2", file=sys.stderr)
        return 2
    drills = [v[3] for v in vias]
    sizes = [v[2] for v in vias]
    print(f"U2=({ux:.3f},{uy:.3f}) vias_in_{args.radius}mm={len(vias)}")
    print(
        f"drill min/med/max={min(drills):.3f}/{statistics.median(drills):.3f}/{max(drills):.3f}"
    )
    print(
        f"pad  min/med/max={min(sizes):.3f}/{statistics.median(sizes):.3f}/{max(sizes):.3f}"
    )
    cur_pad = statistics.median(sizes)
    gaps_cur = pair_gaps(vias, cur_pad)
    gaps_tgt = pair_gaps(vias, args.target_pad)
    print(
        f"copper_gap@{cur_pad:.2f} min/med={min(gaps_cur):.3f}/{statistics.median(gaps_cur):.3f}"
    )
    print(
        f"copper_gap@{args.target_pad:.2f} min/med={min(gaps_tgt):.3f}/{statistics.median(gaps_tgt):.3f}"
    )
    bad = sum(1 for g in gaps_tgt if g < args.min_gap)
    print(f"pairs_below_{args.min_gap}_with_pad_{args.target_pad}={bad}")
    if bad:
        print("RESULT: FAIL — expand via ring / thin density before 0.30 drill")
        return 1
    print("RESULT: PASS — geometry supports target pad at current via sites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
