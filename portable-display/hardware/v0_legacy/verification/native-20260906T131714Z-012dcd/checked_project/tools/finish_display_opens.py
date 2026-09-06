#!/usr/bin/env python3
"""Finish remaining display opens on a candidate board. Not a fab signoff.

Starts from the restored/routed display-island candidate, opens a front-copper
MIPI corridor, escapes LCD_EN/LCD_TE, stitches leftover GND/LCD_3V3, then
routes the 1-lane MIPI pair. Native refill/DRC remain authoritative.
"""
from __future__ import annotations
import argparse, json, math, sys
from pathlib import Path
import shapely
from shapely.geometry import LineString, Point
from kicad_sexpr import load, dump, children, val, values
from geometry_audit import board_items, connected_groups, issues
from route_minboot import Router, CLEAR, HOLE_CU, HOLE_HOLE
from complete_display import DisplayClosure
import complete_minboot as closure_mod

W = 0.09
PWR = 0.25


def pad(items, ref, pin):
    for i in items:
        if i.kind == "pad" and i.ref == ref and i.pin == str(pin):
            return i
    raise KeyError(f"{ref}.{pin}")


def blocker(r, item, net):
    geom, layers, hole = item.geom, item.layers, item.hole
    hits = []
    for it in r.items:
        same = bool(it.net) and it.net == net
        if not same and it.layers & layers:
            d = it.geom.distance(geom)
            if d < CLEAR - 1e-5:
                hits.append(("clearance", d, it))
        if hole is not None and it.hole is not None:
            d = hole.distance(it.hole)
            if d < HOLE_HOLE - 1e-5:
                hits.append(("hole", d, it))
        if not same:
            if hole is not None and it.layers:
                d = hole.distance(it.geom)
                if d < HOLE_CU - 1e-5:
                    hits.append(("hole-cu", d, it))
            if it.hole is not None and layers:
                d = it.hole.distance(geom)
                if d < HOLE_CU - 1e-5:
                    hits.append(("cu-hole", d, it))
    hits.sort(key=lambda x: x[1])
    return hits[:4]


def describe(it):
    extra = ""
    if it.kind == "pad":
        extra = f"{it.ref}.{it.pin} {tuple(round(x, 3) for x in it.pos)}"
    elif it.kind == "via":
        extra = str(tuple(round(x, 3) for x in it.pos))
    elif it.kind == "track":
        extra = f"{tuple(round(x, 3) for x in it.pos[0])}->{tuple(round(x, 3) for x in it.pos[1])} {sorted(it.layers)}"
    return f"{it.kind}:{it.net}:{extra}"


def try_commit(r, pieces, net=None):
    ok = r.commit(pieces)
    if ok:
        return True, []
    # Replay the first failing piece for diagnostics.
    saved = list(r.items)
    hits = []
    for kind, args in pieces:
        if kind == "seg":
            node, item = r._seg_item(*args)
            probe_net = args[6]
        else:
            node, item = r._via_item(*args)
            probe_net = args[2]
        hits = blocker(r, item, probe_net)
        if hits:
            r.items = saved
            return False, hits
        r.items.append(item)
    r.items = saved
    return False, hits


def remove_tracks(r, pred):
    drop = {id(i.node) for i in r.items if pred(i)}
    r.board[:] = [x for x in r.board if id(x) not in drop]
    r._rebuild()
    return len(drop)


def open_key_up_corridor(r):
    """Jog KEY_UP south between x=27.05-29.15 so MIPI can keep F.Cu."""
    bar = None
    for i in r.items:
        if i.kind != "track" or i.net != "KEY_UP" or "F.Cu" not in i.layers:
            continue
        (x1, y1), (x2, y2) = i.pos
        if abs(y1 - 47.55) < 0.02 and abs(y2 - 47.55) < 0.02 and abs(x2 - x1) > 5:
            bar = i
            break
    if bar is None:
        print("KEY_UP F.Cu bar already absent", flush=True)
        return True
    remove_tracks(r, lambda i: i.node is bar.node)
    pieces = [
        ("seg", (24.55, 47.55, 27.05, 47.55, W, "F.Cu", "KEY_UP", "ku-a")),
        ("seg", (27.05, 47.55, 27.05, 46.5, W, "F.Cu", "KEY_UP", "ku-b")),
        ("seg", (27.05, 46.5, 29.15, 46.5, W, "F.Cu", "KEY_UP", "ku-c")),
        ("seg", (29.15, 46.5, 29.15, 47.55, W, "F.Cu", "KEY_UP", "ku-d")),
        ("seg", (29.15, 47.55, 34.3, 47.55, W, "F.Cu", "KEY_UP", "ku-e")),
    ]
    ok, hits = try_commit(r, pieces)
    print("KEY_UP corridor", ok, [describe(h[2]) for h in hits], flush=True)
    return ok


def _poly_path(r, net, pts, via, width=W):
    pieces = [("seg", (*a, *b, width, "F.Cu", net, f"{net}-esc-{j}")) for j, (a, b) in enumerate(zip(pts, pts[1:]))]
    pieces.append(("via", (*via, net, f"{net}-escvia")))
    ok, hits = try_commit(r, pieces)
    print(net, "escape", via, ok, [describe(h[2]) for h in hits[:3]], flush=True)
    return ok


def escape_lcd_te(r):
    """F.Cu snake through the 0.12 mm channel south of U2.1 / north of PWRON_N."""
    te = pad(r.items, "U2", "3").pos
    inner, ych = 25.82, 52.04
    pts = [te, (inner, te[1]), (inner, ych), (23.0, ych), (23.0, 50.6)]
    pieces = [("seg", (*a, *b, W, "F.Cu", "LCD_TE", f"te-{j}")) for j, (a, b) in enumerate(zip(pts, pts[1:]))]
    ok, hits = try_commit(r, pieces)
    print("LCD_TE snake", ok, [describe(h[2]) for h in hits[:3]], flush=True)
    return ok


def escape_lcd_en(r):
    """Short inner stub so the closer can see a free cell; via will not fit."""
    en = pad(r.items, "U2", "4").pos
    inner = 25.82
    pts = [en, (inner, en[1]), (inner, 55.2)]
    pieces = [("seg", (*a, *b, W, "F.Cu", "LCD_EN", f"en-{j}")) for j, (a, b) in enumerate(zip(pts, pts[1:]))]
    ok, hits = try_commit(r, pieces)
    print("LCD_EN stub", ok, [describe(h[2]) for h in hits[:3]], flush=True)
    return ok


def fine_close(board, filled, net):
    """Denser grid / larger seed ring for SoC-side GPIO."""
    saved = (closure_mod.STEP, closure_mod.NX, closure_mod.NY, closure_mod.ORIGIN)
    closure_mod.STEP = 0.08
    closure_mod.ORIGIN = 0.75
    closure_mod.NX = int((57.25 - closure_mod.ORIGIN) / closure_mod.STEP) + 1
    closure_mod.NY = int((109.25 - closure_mod.ORIGIN) / closure_mod.STEP) + 1
    r = DisplayClosure(board, filled)

    def seeds(self, anchors):
        seeds = {}
        step, origin, nx, ny = closure_mod.STEP, closure_mod.ORIGIN, closure_mod.NX, closure_mod.NY
        for x, y, l in anchors:
            ix, iy = round((x - origin) / step), round((y - origin) / step)
            opts = []
            for dy in range(-12, 13):
                for dx in range(-12, 13):
                    jx, jy = ix + dx, iy + dy
                    if not (0 <= jx < nx and 0 <= jy < ny) or self.block[l, jy, jx]:
                        continue
                    px, py = origin + jx * step, origin + jy * step
                    opts.append((math.hypot(px - x, py - y), jx, jy, px, py))
            count = 0
            for dist, jx, jy, px, py in sorted(opts):
                if shapely.intersects(self.obs[l], LineString([(x, y), (px, py)])):
                    continue
                k = (l, jy, jx)
                if k not in seeds or dist < seeds[k][0]:
                    seeds[k] = (dist, (x, y, l))
                count += 1
                if count >= 16:
                    break
        return seeds

    r.seeds = seeds.__get__(r, DisplayClosure)
    try:
        ok = r.close(net)
    finally:
        closure_mod.STEP, closure_mod.NX, closure_mod.NY, closure_mod.ORIGIN = saved
    return ok, r


def stitch_j4_43(r):
    p = pad(r.items, "J4", "43")
    x, y = p.pos
    # Same-net neighbor pads first.
    for pin, (tx, ty) in (("45", (36.6, 39.0)), ("41", (35.4, 39.0)), ("44", (36.3, 35.935))):
        ok, _ = try_commit(r, [("seg", (x, y, tx, ty, 0.12, "F.Cu", "GND", f"j43-to-{pin}"))])
        if ok:
            print("J4.43 stitch pad", pin, flush=True)
            return True
    for vx, vy in [(36.0, 38.2), (36.0, 40.2), (36.45, 39.7), (35.55, 39.7), (36.0, 37.6)]:
        ok, _ = try_commit(r, [
            ("seg", (x, y, vx, vy, 0.12, "F.Cu", "GND", f"j43-{vx}-{vy}")),
            ("via", (vx, vy, "GND", f"j43via-{vx}-{vy}")),
        ])
        if ok:
            print("J4.43 via", (vx, vy), flush=True)
            return True
    print("J4.43 stitch failed", flush=True)
    return False


def close_lcd_3v3(r):
    groups = [g for g in connected_groups([i for i in r.items if i.net == "LCD_3V3"]) if any(i.kind == "pad" for i in g)]
    if len(groups) <= 1:
        return True
    # Direct C29 stub toward U8 if the generic closer fails.
    c29 = pad(r.items, "C29", "1")
    u8 = pad(r.items, "U8", "6")
    if r._manhattan(*c29.pos, *u8.pos, "F.Cu", PWR, "LCD_3V3", "c29-u8"):
        print("LCD_3V3 C29 manhattan", flush=True)
        return True
    if r._manhattan(*c29.pos, *u8.pos, "B.Cu", PWR, "LCD_3V3", "c29-u8b"):
        # Need vias at both ends.
        print("LCD_3V3 tried B.Cu manhattan without vias; retry via pair", flush=True)
    for vx, vy in [(14.5, 39.2), (15.2, 39.2), (16.2, 39.2), (17.5, 39.2)]:
        pieces = [
            ("seg", (*c29.pos, vx, vy, PWR, "F.Cu", "LCD_3V3", "c29-via")),
            ("via", (vx, vy, "LCD_3V3", "c29via")),
        ]
        ok, _ = try_commit(r, pieces)
        if ok:
            print("LCD_3V3 extra via", (vx, vy), flush=True)
            return False  # still needs closer
    return False


def fanout_mipi_soc(r):
    """Short south/west stubs so D0 clears the SOC_LDO_1V8 fanout."""
    plan = {
        "DSI_CKP": [(27.375, 50.55)],
        "DSI_CKN": [(27.725, 50.55)],
        "DSI_D0P": [(28.775, 50.70), (28.15, 50.35)],
        "DSI_D0N": [(29.125, 50.55), (28.45, 50.20)],
    }
    pads = {
        "DSI_CKP": pad(r.items, "U2", "85").pos,
        "DSI_CKN": pad(r.items, "U2", "84").pos,
        "DSI_D0P": pad(r.items, "U2", "81").pos,
        "DSI_D0N": pad(r.items, "U2", "80").pos,
    }
    ok = True
    for net, pts in plan.items():
        cur = pads[net]
        for j, nxt in enumerate(pts):
            committed, hits = try_commit(r, [("seg", (*cur, *nxt, W, "F.Cu", net, f"mipi-fan-{net}-{j}"))])
            if not committed:
                print("MIPI fanout fail", net, cur, nxt, [describe(h[2]) for h in hits], flush=True)
                ok = False
                break
            cur = nxt
        else:
            print("MIPI fanout", net, "->", cur, flush=True)
    return ok


def pair_trunk(r, name, start, end, layer="F.Cu"):
    """Coupled 0.09/0.09 candidate trunk. Impedance is not signed off."""
    import heapq
    import numpy as np
    import shapely
    from shapely.ops import unary_union
    nets = ["DSI_" + name + "P", "DSI_" + name + "N"]
    offset = (W + W) / 2  # 0.09: pair centers 0.18 mm apart
    obs = []
    for i in r.items:
        if i.net in nets:
            continue
        if layer in i.layers:
            obs.append(i.geom.buffer(0.092 + (2 * W + W) / 2))
        if i.hole is not None:
            obs.append(i.hole.buffer(0.252 + (2 * W + W) / 2))
    poly = unary_union(obs)
    shapely.prepare(poly)
    x0, y0, step = 18.0, 34.0, 0.05
    nx, ny = 800, 400
    yy, xx = np.mgrid[0:ny, 0:nx]
    block = shapely.intersects_xy(poly.buffer(step * 0.71), x0 + xx * step, y0 + yy * step)

    def cell(x, y):
        return (round((x - x0) / step), round((y - y0) / step))

    def xy(k):
        return (x0 + k[0] * step, y0 + k[1] * step)

    sx, sy = start
    tx, ty = end
    start_c, goal_c = cell(sx, sy), cell(tx, ty)
    if not (0 <= start_c[0] < nx and 0 <= start_c[1] < ny and 0 <= goal_c[0] < nx and 0 <= goal_c[1] < ny):
        print(name, "pair cell out of range", start_c, goal_c, flush=True)
        return False
    if block[start_c[1], start_c[0]] or block[goal_c[1], goal_c[0]]:
        print(name, "blocked pair access", flush=True)
        return False
    dist = {start_c: 0}
    parent = {}
    heap = [(math.dist(start_c, goal_c) * step, 0, start_c)]
    done = set()
    end_c = None
    while heap:
        _, c, k = heapq.heappop(heap)
        if k in done:
            continue
        done.add(k)
        if k == goal_c:
            end_c = k
            break
        for dx, dy in [(0, -1), (1, 0), (-1, 0), (0, 1), (1, -1), (-1, -1), (1, 1), (-1, 1)]:
            nk = (k[0] + dx, k[1] + dy)
            if not (0 <= nk[0] < nx and 0 <= nk[1] < ny) or block[nk[1], nk[0]] or nk in done:
                continue
            nc = c + math.hypot(dx, dy) * step
            if nc >= dist.get(nk, 1e9):
                continue
            dist[nk] = nc
            parent[nk] = k
            heapq.heappush(heap, (nc + math.dist(nk, goal_c) * step, nc, nk))
    if end_c is None:
        print(name, "no paired corridor", len(done), flush=True)
        return False
    path = [end_c]
    while path[-1] in parent:
        path.append(parent[path[-1]])
    path.reverse()
    points = [(sx, sy)] + [xy(k) for k in path] + [(tx, ty)]
    merged = []
    for p in points:
        if merged and math.dist(p, merged[-1]) < 1e-8:
            continue
        while len(merged) > 1:
            a, b = merged[-2:]
            if abs((b[0] - a[0]) * (p[1] - b[1]) - (b[1] - a[1]) * (p[0] - b[0])) > 1e-8:
                break
            merged.pop()
        merged.append(p)
    line = LineString(merged)
    pieces = []
    lengths = {}
    for net, sign in zip(nets, [-1, 1]):
        curve = line.offset_curve(sign * offset, join_style="mitre")
        if curve.geom_type != "LineString":
            print(name, "offset split", flush=True)
            return False
        pts = list(curve.coords)
        pieces += [("seg", (*a, *b, W, layer, net, f"mipi-{name}-{net}-{j}")) for j, (a, b) in enumerate(zip(pts, pts[1:]))]
        lengths[net] = curve.length
    ok, hits = try_commit(r, pieces)
    print(name, "paired route", ok, lengths, [describe(h[2]) for h in hits[:3]], flush=True)
    return ok


def connect_j4_mipi(r):
    """P pads stay on F.Cu; N pads drop to B.Cu to clear the ELVDD row."""
    ends = {
        "DSI_CKP": pad(r.items, "J4", "39").pos,
        "DSI_CKN": pad(r.items, "J4", "40").pos,
        "DSI_D0P": pad(r.items, "J4", "35").pos,
        "DSI_D0N": pad(r.items, "J4", "36").pos,
    }
    # Last MIPI copper of each net is the current island near y~41.
    result = {}
    for net, dest in ends.items():
        copper = [i for i in r.items if i.net == net and i.kind == "track"]
        if not copper:
            result[net] = False
            continue
        # Closest track endpoint to destination.
        pts = []
        for i in copper:
            pts.extend(i.pos)
        src = min(pts, key=lambda p: math.dist(p, dest))
        if net.endswith("P"):
            result[net] = r._manhattan(*src, *dest, "F.Cu", W, net, "j4-" + net)
            print(net, "J4 F.Cu", result[net], src, dest, flush=True)
            continue
        # N: via near the trunk, B.Cu to a via beside the even pad, F.Cu into the pad.
        vx1, vy1 = round(src[0], 3), round(src[1], 3)
        vx2, vy2 = dest[0], dest[1] - 0.8
        options = [
            ((vx1, vy1), (dest[0], dest[1] - 0.9)),
            ((src[0], src[1] - 0.4), (dest[0], dest[1] - 0.9)),
            ((src[0] + 0.3, src[1]), (dest[0] + 0.4, dest[1] - 0.7)),
            ((src[0] - 0.3, src[1]), (dest[0] - 0.3, dest[1] - 0.7)),
        ]
        done = False
        for a, b in options:
            pieces = [
                ("seg", (*src, *a, W, "F.Cu", net, "n-entry")),
                ("via", (*a, net, "n-via1")),
                ("seg", (*a, *b, W, "B.Cu", net, "n-bcu")),
                ("via", (*b, net, "n-via2")),
                ("seg", (*b, *dest, W, "F.Cu", net, "n-pad")),
            ]
            ok, hits = try_commit(r, pieces)
            if ok:
                print(net, "J4 N via-pair", a, b, flush=True)
                done = True
                break
        if not done:
            # Fall back to manhattan on either layer.
            done = r._manhattan(*src, *dest, "F.Cu", W, net, "j4n-f") or r._manhattan(*src, *dest, "B.Cu", W, net, "j4n-b")
            print(net, "J4 N fallback", done, [describe(h[2]) for h in hits[:3]] if not done else "", flush=True)
        result[net] = done
    return result


def islands(items, net):
    return [g for g in connected_groups([i for i in items if i.net == net]) if any(i.kind == "pad" for i in g)]


def report_opens(items, nets):
    out = {}
    for net in nets:
        g = islands(items, net)
        out[net] = len(g)
        if len(g) > 1:
            print(net, "islands", len(g), [[f"{i.ref}.{i.pin}" for i in gg if i.kind == "pad"][:6] for gg in g], flush=True)
    return out


def main():
    raise SystemExit("Historical candidate router disabled: single-net MIPI and layer-only fallbacks do not prove connectivity. Use complete_display.py for low-speed nets and route_display_pairs.py for paired candidates; validate with native KiCad. See docs/DISPLAY_PCB_STATUS.md.")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--filled", type=Path, required=True)
    a = p.parse_args()
    b = load(a.input)
    filled = load(a.filled)
    r = DisplayClosure(b, filled)
    result = {}
    result["key_up_corridor"] = open_key_up_corridor(r)
    result["j4_43"] = stitch_j4_43(r)
    result["lcd_te_escape"] = escape_lcd_te(r)
    result["lcd_en_escape"] = escape_lcd_en(r)
    result["c29"] = close_lcd_3v3(r)
    original = closure_mod.width_for
    closure_mod.width_for = lambda n: PWR if n in {"LCD_3V3", "LCD_1V8", "ELVDD", "ELVSS"} else original(n)
    for net in ["LCD_TE", "LCD_3V3", "KEY_DOWN"]:
        print("CLOSE", net, flush=True)
        result[net] = r.close(net)
        print("RESULT", net, result[net], flush=True)
        r._strip_zone_fills()
    print("CLOSE LCD_EN fine", flush=True)
    ok, r2 = fine_close(r.board, filled, "LCD_EN")
    r = r2
    result["LCD_EN"] = ok
    print("RESULT LCD_EN", ok, flush=True)
    r._strip_zone_fills()
    result["mipi_fanout"] = fanout_mipi_soc(r)
    for net in ["DSI_CKP", "DSI_CKN", "DSI_D0P", "DSI_D0N"]:
        if len(islands(r.items, net)) > 1:
            print("CLOSE", net, flush=True)
            result[net] = r.close(net)
            print("RESULT", net, result[net], flush=True)
            r._strip_zone_fills()
        else:
            result[net] = True
    r._strip_zone_fills()
    dump(r.board, a.output)
    opens = report_opens(board_items(b), [
        "LCD_EN", "LCD_TE", "LCD_RST", "LCD_3V3", "LCD_1V8", "LCD_SWIRE",
        "ELVDD", "ELVSS", "DSI_CKP", "DSI_CKN", "DSI_D0P", "DSI_D0N", "KEY_DOWN",
    ])
    geom = issues(board_items(b))
    summary = {
        "result": result,
        "pad_islands": opens,
        "geometry_issues": geom,
        "tracks_added": r.report["added_tracks"],
        "vias_added": r.report["added_vias"],
        "impedance_verified": False,
        "fabrication_released": False,
    }
    a.output.with_suffix(".opens.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("pad_islands", "tracks_added", "vias_added")}, indent=2))
    print("geometry", len(geom), flush=True)


if __name__ == "__main__":
    main()
