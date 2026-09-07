#!/usr/bin/env python3
"""Remove SPI NAND island; keep TF boot straps (BOOT0/BOOT1) and FEL."""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V0 = ROOT.parent / "v0_legacy"
sys.path.insert(0, str(V0 / "tools"))
from kicad_sexpr import load, children, val, values, props, Q  # noqa: E402

DELETE_REFS = {"U3", "C22", "R7", "R8", "R9"}
DELETE_NETS = {"NAND_CLK", "NAND_CS", "NAND_HOLD", "NAND_WP"}
RENAME = {"NAND_MOSI": "BOOT0", "NAND_MISO": "BOOT1"}
U2_NC = {
    "56": "unconnected-(U2-PC1_SPI0_CS-Pad56)",
    "57": "unconnected-(U2-PC0_SPI0_CLK-Pad57)",
    "60": "unconnected-(U2-PC5_SPI0_HOLD-Pad60)",
    "61": "unconnected-(U2-PC4_SPI0_WP-Pad61)",
}
LIB_DROP = {
    "Sameat:U3_W25N01GVZEIG",
    "Sameat:C22_100n",
    "Sameat:R7_10k",
    "Sameat:R8_10k",
    "Sameat:R9_10k",
}
# Schematic labels that only existed for deleted parts (after MOSI/MISO rename).
DROP_LABEL_AT = {
    (24.130, 163.830),  # U3 CS
    (24.130, 161.290),  # U3 MISO / BOOT1
    (24.130, 158.750),  # U3 WP
    (24.130, 156.210),  # U3 GND
    (54.610, 163.830),  # U3 MOSI / BOOT0
    (54.610, 161.290),  # U3 CLK
    (54.610, 158.750),  # U3 HOLD
    (54.610, 156.210),  # U3 3V3
    (95.250, 160.020),  # C22 3V3
    (125.730, 160.020),  # C22 GND
    (165.100, 160.020),  # R7 3V3
    (195.580, 160.020),  # R7 CS
    (24.130, 185.420),  # R8 3V3
    (54.610, 185.420),  # R8 WP
    (95.250, 185.420),  # R9 3V3
    (125.730, 185.420),  # R9 HOLD
}
U2_NC_AT = {
    (320.040, 168.910),  # CS
    (320.040, 166.370),  # CLK
    (320.040, 158.750),  # HOLD
    (320.040, 156.210),  # WP
}


def qstr(x):
    return str(x)


def net_of(node):
    n = values(node, "net")
    if not n:
        return ""
    return qstr(n[-1])


def set_net(node, name):
    z = None
    for c in node:
        if isinstance(c, list) and c and c[0] == "net":
            z = c
            break
    if name is None:
        if z is not None:
            node.remove(z)
        return
    quoted = Q(name)
    if z is None:
        node.append(["net", quoted])
    else:
        z[:] = ["net", quoted]


def at_xy(node):
    v = values(node, "at")
    return (round(float(v[0]), 3), round(float(v[1]), 3))


def rotation(x, y, deg):
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def fp_ref(fp):
    return str(props(fp).get("Reference", ""))


def dump_item(item, indent=1):
    """Serialize one top-level child the same way kicad_sexpr.dumps does."""
    from kicad_sexpr import dumps
    return "\t" * indent + dumps(item, indent)


def rewrite_root(path, new_children_fn, header_keys=None):
    """Load, replace children after a predicate, dump whole file.

    Used only for the schematic (generated, compact-enough).
    """
    from kicad_sexpr import dump, dumps
    tree = load(path)
    new_children_fn(tree)
    path.write_text(dumps(tree) + "\n", encoding="utf-8")


def edit_schematic():
    from kicad_sexpr import dumps

    sch = V0 / "02_soc_v851s.kicad_sch"
    tree = load(sch)
    tb = next(c for c in tree if isinstance(c, list) and c and c[0] == "title_block")
    for c in tb:
        if isinstance(c, list) and c[0] == "title":
            c[1] = Q("02 V851s / Boot / TF")
        if isinstance(c, list) and c[0] == "comment" and str(c[1]) == "1":
            c[2] = Q("TF-only boot; SPI NAND island removed")

    out = []
    for item in tree:
        if not isinstance(item, list) or not item:
            out.append(item)
            continue
        kind = item[0]
        if kind == "lib_symbols":
            kept_syms = []
            for s in item[1:]:
                if isinstance(s, list) and s and s[0] == "symbol" and str(s[1]) in LIB_DROP:
                    continue
                if isinstance(s, list) and s and s[0] == "symbol":
                    for p in children(s, "property"):
                        if str(p[1]) == "Description" and "SPI NAND boot" in str(p[2]):
                            p[2] = Q("PC3 BOOT1 pull-up; BOOT_SEL=11 TF first")
                kept_syms.append(s)
            item[:] = [item[0]] + kept_syms
            out.append(item)
            continue
        if kind == "symbol":
            lib_id = str(val(item, "lib_id", ""))
            if lib_id in LIB_DROP:
                continue
            for p in children(item, "property"):
                if str(p[1]) == "Description" and "SPI NAND boot" in str(p[2]):
                    p[2] = Q("PC3 BOOT1 pull-up; BOOT_SEL=11 TF first")
            out.append(item)
            continue
        if kind == "global_label":
            xy = at_xy(item)
            name = str(item[1])
            if name in RENAME:
                item[1] = Q(RENAME[name])
                name = RENAME[name]
            if xy in DROP_LABEL_AT:
                continue
            if xy in U2_NC_AT:
                uuid = str(val(item, "uuid"))
                at = values(item, "at")
                out.append(["no_connect", ["at", at[0], at[1]], ["uuid", Q(uuid)]])
                continue
            if name in DELETE_NETS:
                continue
            out.append(item)
            continue
        out.append(item)

    sch.write_text(dumps(out) + "\n", encoding="utf-8")
    print("schematic", sch)


def snap(p, n=3):
    return (round(float(p[0]), n), round(float(p[1]), n))


def pad_world(fp, pad):
    x, y, *angles = map(float, values(fp, "at"))
    fa = angles[0] if angles else 0
    px, py, *pa = map(float, values(pad, "at"))
    px, py = rotation(px, py, fa)
    return (px + x, py + y)


def copper_net(node):
    return net_of(node)


def prune_graph(segments, keep_pts, tol=0.15):
    """Keep segments on paths between keep_pts; drop leaves that are not keep pads."""
    def near(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol

    nodes = []

    def nid(p):
        p = snap(p, 4)
        for i, q in enumerate(nodes):
            if near(p, q):
                return i
        nodes.append(p)
        return len(nodes) - 1

    edges = []  # (a,b,seg_index)
    for i, seg in enumerate(segments):
        a = snap(values(seg, "start")[:2], 4)
        b = snap(values(seg, "end")[:2], 4)
        edges.append((nid(a), nid(b), i))

    keep_n = set()
    for p in keep_pts:
        for i, q in enumerate(nodes):
            if near(p, q):
                keep_n.add(i)

    adj = defaultdict(list)
    for a, b, i in edges:
        adj[a].append((b, i))
        adj[b].append((a, i))

    # BFS from keep nodes
    seen = set(keep_n)
    stack = list(keep_n)
    while stack:
        u = stack.pop()
        for v, _i in adj[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)

    # Iteratively prune degree-1 nodes that are not keep
    alive_edges = {i for a, b, i in edges if a in seen and b in seen}
    changed = True
    while changed:
        changed = False
        deg = defaultdict(int)
        for a, b, i in edges:
            if i not in alive_edges:
                continue
            deg[a] += 1
            deg[b] += 1
        drop_nodes = {n for n, d in deg.items() if d == 1 and n not in keep_n}
        if not drop_nodes:
            break
        new_alive = set()
        for a, b, i in edges:
            if i not in alive_edges:
                continue
            if a in drop_nodes or b in drop_nodes:
                changed = True
                continue
            new_alive.add(i)
        alive_edges = new_alive

    return alive_edges


def edit_pcb():
    pcb_path = ROOT / "ak_display_38x64_PLACEMENT_ONLY.kicad_pcb"
    board = load(pcb_path)

    deleted_pad_pts = []  # (x,y,net)
    keep_boot = {"BOOT0": [], "BOOT1": []}

    new_board = []
    for item in board:
        if not isinstance(item, list) or not item:
            new_board.append(item)
            continue
        kind = item[0]
        if kind == "footprint":
            ref = fp_ref(item)
            if ref in DELETE_REFS:
                for pad in children(item, "pad"):
                    deleted_pad_pts.append((pad_world(item, pad), net_of(pad)))
                continue
            # rename / NC pads
            for pad in children(item, "pad"):
                n = net_of(pad)
                pin = str(pad[1])
                if ref == "U2" and pin in U2_NC:
                    set_net(pad, U2_NC[pin])
                    continue
                if n in RENAME:
                    set_net(pad, RENAME[n])
                    n = RENAME[n]
                if n in ("BOOT0", "BOOT1"):
                    keep_boot[n].append(pad_world(item, pad))
                if n in DELETE_NETS:
                    # leftover pull-up pads should not remain
                    set_net(pad, n)  # shouldn't happen on remaining fps
            for p in children(item, "property"):
                if str(p[1]) == "Description" and "SPI NAND boot" in str(p[2]):
                    p[2] = Q("PC3 BOOT1 pull-up; BOOT_SEL=11 TF first")
            new_board.append(item)
            continue
        new_board.append(item)

    # Second pass: copper
    boot_segs = {"BOOT0": [], "BOOT1": []}
    filtered = []
    for item in new_board:
        if not isinstance(item, list) or not item:
            filtered.append(item)
            continue
        kind = item[0]
        if kind in ("segment", "via"):
            n = net_of(item)
            if n in RENAME:
                set_net(item, RENAME[n])
                n = RENAME[n]
            if n in DELETE_NETS:
                continue
            if n in ("BOOT0", "BOOT1") and kind == "segment":
                boot_segs[n].append(item)
                continue
            if n in ("BOOT0", "BOOT1") and kind == "via":
                # keep via only if later connected; drop for now if it was NAND-only
                boot_segs[n].append(item)
                continue
            if n in ("3V3", "GND") and kind == "segment":
                a = tuple(map(float, values(item, "start")[:2]))
                b = tuple(map(float, values(item, "end")[:2]))
                drop = False
                for (px, py), pn in deleted_pad_pts:
                    if pn in (n, "3V3", "GND") or True:
                        if math.hypot(a[0] - px, a[1] - py) < 0.2 or math.hypot(b[0] - px, b[1] - py) < 0.2:
                            # only drop if this end is at a deleted pad of same net
                            if pn == n and (
                                math.hypot(a[0] - px, a[1] - py) < 0.2
                                or math.hypot(b[0] - px, b[1] - py) < 0.2
                            ):
                                drop = True
                                break
                if drop:
                    continue
            filtered.append(item)
            continue
        filtered.append(item)

    # Prune BOOT0/BOOT1 extra stubs that only served U3
    final = []
    boot_keep_idx = {}
    for net, segs in boot_segs.items():
        segs_only = [s for s in segs if s[0] == "segment"]
        vias = [s for s in segs if s[0] == "via"]
        alive = prune_graph(segs_only, keep_boot[net])
        boot_keep_idx[net] = (alive, segs_only, vias)

    # insert pruned boot copper before closing; keep original relative order:
    # rebuild by walking filtered + injecting kept boot copper where first boot item was
    injected = False
    out = []
    for item in filtered:
        out.append(item)
    # append kept boot copper at end (before last ')') — they were collected out
    for net in ("BOOT0", "BOOT1"):
        alive, segs_only, vias = boot_keep_idx[net]
        for i, seg in enumerate(segs_only):
            if i in alive:
                out.append(seg)
        # vias: keep if near a kept segment endpoint
        pts = []
        for i, seg in enumerate(segs_only):
            if i in alive:
                pts.append(tuple(map(float, values(seg, "start")[:2])))
                pts.append(tuple(map(float, values(seg, "end")[:2])))
        pts += keep_boot[net]
        for v in vias:
            p = tuple(map(float, values(v, "at")[:2]))
            if any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.2 for q in pts):
                out.append(v)

    from kicad_sexpr import dumps
    pcb_path.write_text(dumps(out) + "\n", encoding="utf-8")
    print("pcb", pcb_path, "footprints", sum(1 for x in out if isinstance(x, list) and x and x[0] == "footprint"))
    return out


def edit_maps(board):
    mapping = {}
    for fp in children(board, "footprint"):
        ref = fp_ref(fp)
        mapping[ref] = {str(p[1]): net_of(p) for p in children(fp, "pad")}
    (ROOT / "source_pad_net_map.json").write_text(
        json.dumps(mapping, indent=2) + "\n", encoding="utf-8"
    )
    csv = ROOT / "placement_coordinates.csv"
    rows = csv.read_text(encoding="utf-8").splitlines()
    hdr, body = rows[0], rows[1:]
    kept = [hdr]
    for line in body:
        ref = line.split(",", 1)[0]
        if ref not in DELETE_REFS:
            kept.append(line)
    csv.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print("maps", len(mapping), "csv", len(kept) - 1)


def edit_pin_contract():
    p = V0 / "design" / "pin_contract.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    comps = data["components"]
    for ref in list(DELETE_REFS):
        comps.pop(ref, None)
    u2 = comps["U2"]["pins"]
    u2["56"]["net"] = None
    u2["57"]["net"] = None
    u2["58"]["net"] = "BOOT1"
    u2["59"]["net"] = "BOOT0"
    u2["60"]["net"] = None
    u2["61"]["net"] = None
    for ref in ("J3", "SW6", "R10"):
        for pin in comps[ref]["pins"].values():
            if pin.get("net") == "NAND_MOSI":
                pin["net"] = "BOOT0"
    comps["R28"]["pins"]["2"]["net"] = "BOOT1"
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("pin_contract")


def edit_route_script():
    p = ROOT / "tools" / "route_board.py"
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        '    "NAND_CLK", "NAND_CS", "NAND_MISO", "NAND_MOSI", "NAND_HOLD", "NAND_WP",\n',
        '    "BOOT0", "BOOT1",\n',
    )
    p.write_text(t, encoding="utf-8")
    print("route_board.py")


if __name__ == "__main__":
    edit_schematic()
    board = edit_pcb()
    edit_maps(board)
    edit_pin_contract()
    edit_route_script()
