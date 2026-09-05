#!/usr/bin/env python3
"""Append Minboot copper to the existing PCB. Does not regenerate the board.

Default is dry-run. Pass --write to update portable_display_epass.kicad_pcb.
Display-island nets stay unrouted except local LCD_3V3 pour stitching.
"""
from __future__ import annotations
import argparse, heapq, json, math, sys
from collections import defaultdict
from pathlib import Path
import generate_evt1 as gen
from geometry_audit import board_items, connected_groups, issues, rotation
from kicad_sexpr import Q, load, dump, loads, children, child, val, values, props, setval
from shapely.geometry import Point, LineString, Polygon, box
from shapely import affinity

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "portable_display_epass.kicad_pcb"
VIA = 0.40
DRILL = 0.20
CLEAR = 0.09
HOLE_CU = 0.25
HOLE_HOLE = 0.25
EDGE = 0.5
GRID = 0.25
SIG_W = 0.09
PWR_W = 0.25
USB_W = 0.09
CORE_POLY = Polygon([(2, 82), (15, 82), (15, 64), (21, 64), (21, 48), (38, 48), (38, 64), (25, 64), (25, 100), (2, 100)])
POUR_1V8 = Polygon([(12, 46), (46, 46), (46, 76), (24, 76), (24, 100), (12, 100)])
POUR_DRAM = Polygon([(2, 86), (10, 86), (10, 100), (2, 100)])
POUR_RTC = Polygon([(4, 14), (36, 14), (36, 32), (6, 32), (6, 92), (20, 92), (20, 78), (4, 78)])
POUR_LCD = Polygon([(14, 36), (34, 36), (34, 44), (14, 44)])
STITCH_POUR = {
    "GND": None,  # full In1
    "3V3": "outside_core",
    "CORE_0V93": CORE_POLY,
    "1V8": POUR_1V8,
    "DRAM_1V5": POUR_DRAM,
    "RTC_3V3": POUR_RTC,
    "LCD_3V3": POUR_LCD,
}
PRIORITY = [
    "LX_3V3", "LX_CORE", "LX_DRAM", "XIN", "XOUT",
    "VREF", "PMIC_BACKUP", "VBUS", "VBAT", "VSYS",
    "USB_CC1", "USB_CC2", "USB_DP", "USB_DM",
    "UART0_TX", "UART0_RX", "E907_TX", "E907_RX",
    "PMIC_SCL", "PMIC_SDA", "PMIC_IRQ_N", "PWRON_N",
    "CHGLED_A", "CHGLED_N", "BAT_NTC",
    "NAND_CLK", "NAND_CS", "NAND_MISO", "NAND_MOSI", "NAND_HOLD", "NAND_WP",
    "SOC_LDO_1V8", "SOC_AVCC", "VRA1",
    "SD_PWR_EN", "SD_PWR_GATE", "SD_3V3", "SD_CLK", "SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3", "SD_DET",
    "I2C0_SCL", "I2C0_SDA", "ACCEL_INT_N", "RTC_INT_N", "RTC_EVI", "RTC_VBACKUP",
    "WAKE_CEXT", "WAKE_REXT", "WAKE_PULSE", "WAKE_PULSE_N", "WAKE_REQ_N",
    "ADC_KEYS", "KEY_UP", "KEY_DOWN", "KEY_OK", "KEY_BACK",
    "STATUS_LED", "STATUS_LED_A", "LCD_3V3",
]


def net_ids(board):
    return {str(n[2]): int(n[1]) for n in children(board, "net") if len(n) > 2 and str(n[2])}


def max_net_id(board):
    return max(int(n[1]) for n in children(board, "net"))


def add_net(board, name, ids):
    if name in ids:
        return ids[name]
    nid = max_net_id(board) + 1
    nets = children(board, "net")
    board.insert(board.index(nets[-1]) + 1, ["net", nid, Q(name)])
    ids[name] = nid
    return nid


def fp_ref(fp):
    return str(props(fp).get("Reference", ""))


def set_prop(fp, key, value, layer="F.Fab"):
    for p in children(fp, "property"):
        if p[1] == key:
            p[2] = Q(value)
            return
    fp.append(loads(f'(property "{key}" "{value}" (at 0 0 0) (layer "{layer}") (hide yes) (effects (font (size 1 1))))'))


def hide_prop(fp, key):
    for p in children(fp, "property"):
        if p[1] == key:
            if not any(isinstance(x, list) and x and x[0] == "hide" for x in p):
                p.append(["hide", "yes"])
            return


def width_for(net):
    if net in {"USB_DP", "USB_DM"}:
        return USB_W
    if net.startswith("LX_") or net in {"VBUS", "VBAT", "VSYS", "CORE_0V93", "DRAM_1V5", "3V3", "GND", "1V8", "RTC_3V3"}:
        return PWR_W
    return SIG_W


class Router:
    def __init__(self, board):
        self.board = board
        self.ids = net_ids(board)
        self.report = {"moved": [], "hygiene": [], "stitched": [], "routes": {}, "failed": [], "added_tracks": 0, "added_vias": 0}
        self._rebuild()

    def _rebuild(self):
        self.items = board_items(self.board)
        self.groups = connected_groups(self.items)

    def _append(self, node):
        # Insert copper before zones so KiCad still sees zones last.
        zones = [i for i, x in enumerate(self.board) if isinstance(x, list) and x and x[0] == "zone"]
        idx = zones[0] if zones else len(self.board)
        self.board.insert(idx, node)

    def _seg_item(self, x1, y1, x2, y2, width, layer, net, tag):
        text = gen._seg(x1, y1, x2, y2, width, layer, net, self.ids, tag)
        node = loads(text)
        geom = LineString(((x1, y1), (x2, y2))).buffer(width / 2, quad_segs=12)
        item = type(self.items[0])("track", net, frozenset((layer,)), geom, node, str(val(node, "uuid", tag)), None, "", "", ((x1, y1), (x2, y2)))
        return node, item

    def _via_item(self, x, y, net, tag):
        text = gen._via(x, y, net, self.ids, tag)
        node = loads(text)
        geom = Point((x, y)).buffer(VIA / 2, quad_segs=16)
        hole = Point((x, y)).buffer(DRILL / 2, quad_segs=16)
        item = type(self.items[0])("via", net, frozenset(("F.Cu", "In1.Cu", "In2.Cu", "B.Cu")), geom, node, str(val(node, "uuid", tag)), hole, "", "", (x, y))
        return node, item

    def add_seg(self, x1, y1, x2, y2, width, layer, net, tag):
        if math.hypot(x2 - x1, y2 - y1) < 1e-4:
            return False
        node, item = self._seg_item(x1, y1, x2, y2, width, layer, net, tag)
        if not self._item_ok(item, net):
            return False
        self._append(node)
        self.items.append(item)
        self.report["added_tracks"] += 1
        return True

    def add_via(self, x, y, net, tag):
        if not (EDGE + 0.4 <= x <= 58 - EDGE - 0.4 and EDGE + 0.4 <= y <= 110 - EDGE - 0.4):
            return False
        node, item = self._via_item(x, y, net, tag)
        if not self._item_ok(item, net):
            return False
        self._append(node)
        self.items.append(item)
        self.report["added_vias"] += 1
        return True

    def commit(self, pieces):
        """pieces: list of ('seg', args) or ('via', args) checked against a growing snapshot."""
        staged = []
        saved_items = list(self.items)
        for kind, args in pieces:
            if kind == "seg":
                x1, y1, x2, y2, width, layer, net, tag = args
                if math.hypot(x2 - x1, y2 - y1) < 1e-4:
                    continue
                node, item = self._seg_item(x1, y1, x2, y2, width, layer, net, tag)
            else:
                x, y, net, tag = args
                if not (EDGE + 0.4 <= x <= 58 - EDGE - 0.4 and EDGE + 0.4 <= y <= 110 - EDGE - 0.4):
                    self.items = saved_items
                    return False
                node, item = self._via_item(x, y, net, tag)
            if not self._item_ok(item, net):
                self.items = saved_items
                return False
            staged.append((kind, node, item))
            self.items.append(item)
        self.items = saved_items
        for kind, node, item in staged:
            self._append(node)
            self.items.append(item)
            self.report["added_tracks" if kind == "seg" else "added_vias"] += 1
        return True

    def _item_ok(self, item, net):
        geom, layers, hole = item.geom, item.layers, item.hole
        for it in self.items:
            same = bool(it.net) and it.net == net
            if not same and it.layers & layers:
                if it.geom.distance(geom) < CLEAR - 1e-5:
                    return False
            if hole is not None and it.hole is not None:
                if hole.distance(it.hole) < HOLE_HOLE - 1e-5:
                    return False
            if not same:
                if hole is not None and it.layers and hole.distance(it.geom) < HOLE_CU - 1e-5:
                    return False
                if it.hole is not None and layers and it.hole.distance(geom) < HOLE_CU - 1e-5:
                    return False
        return True

    def hygiene(self, devs):
        byref = {fp_ref(f): f for f in children(self.board, "footprint")}
        moves = {"C34": (15.5, 61.0), "R27": (42.0, 52.0)}
        for ref, (x, y) in moves.items():
            fp = byref[ref]
            old = list(map(float, values(fp, "at")))
            rot = old[2] if len(old) > 2 else 0
            setval(fp, "at", x, y, rot)
            self.report["moved"].append({"ref": ref, "old": old, "new": [x, y, rot]})
        for ref in ("H1", "H2", "H3", "H4"):
            fp = byref[ref]
            attrs = child(fp, "attr")
            if attrs is None:
                fp.append(["attr", "board_only", "exclude_from_pos_files", "exclude_from_bom"])
            else:
                words = [str(x) for x in attrs[1:]]
                if "board_only" not in words:
                    attrs.insert(1, "board_only")
            hide_prop(fp, "Reference")
            self.report["hygiene"].append("board_only " + ref)
        for fp in children(self.board, "footprint"):
            ref = fp_ref(fp)
            if ref in devs:
                d = devs[ref]
                if d.datasheet:
                    set_prop(fp, "Datasheet", d.datasheet)
                set_prop(fp, "Description", d.note or "")
        for t in children(self.board, "gr_text"):
            txt = str(t[1])
            if "BATTERY KEEPOUT" in txt:
                eff = child(t, "effects")
                if eff is not None and not any(isinstance(x, list) and x and x[0] == "justify" for x in eff):
                    eff.append(["justify", "mirror"])
                    self.report["hygiene"].append("mirror battery text")
            if "ENGINEERING ONLY" in txt:
                setval(t, "at", 12, 48)
                self.report["hygiene"].append("moved board title")
        self._nc_pads(devs, byref)
        self._strip_zone_fills()

    def _nc_pads(self, devs, byref):
        self.items = board_items(self.board)
        groups = connected_groups(self.items)
        remove = set()
        for ref, d in devs.items():
            fp = byref[ref]
            pads = {str(p[1]): p for p in children(fp, "pad")}
            for pn, (name, net) in d.pins.items():
                if net:
                    continue
                pad = pads[pn]
                uname = f"unconnected-({ref}-{name}-Pad{pn})"
                nid = add_net(self.board, uname, self.ids)
                setval(pad, "net", nid, Q(uname))
                # Drop fanout copper that only served this now-NC pad.
                for g in groups:
                    gpads = [x for x in g if x.kind == "pad"]
                    if not any(x.ref == ref and x.pin == str(pn) for x in gpads):
                        continue
                    foreign = [x for x in gpads if not (x.ref == ref and x.pin == str(pn))]
                    if foreign:
                        continue
                    for x in g:
                        if x.kind in {"track", "via"}:
                            remove.add(id(x.node))
        if remove:
            self.board[:] = [x for x in self.board if id(x) not in remove]
            self.report["hygiene"].append(f"removed {len(remove)} NC fanout copper objects")
        self.ids = net_ids(self.board)

    def _strip_zone_fills(self):
        for zone in children(self.board, "zone"):
            zone[:] = [x for x in zone if not isinstance(x, list) or x[0] not in {"filled_polygon", "fill_segments"}]

    def stitch_planes(self):
        self._rebuild()
        by_net_groups = defaultdict(list)
        for g in self.groups:
            pads = [x for x in g if x.kind == "pad" and x.net]
            if not pads:
                continue
            nets = {x.net for x in pads}
            if len(nets) != 1:
                continue
            by_net_groups[next(iter(nets))].append(g)
        for net, region in STITCH_POUR.items():
            groups = by_net_groups.get(net, [])
            # Prefer stitching pad groups that do not already include a via.
            for gi, g in enumerate(groups):
                if any(x.kind == "via" for x in g):
                    continue
                pads = [x for x in g if x.kind == "pad" and x.net == net]
                smd = [x for x in pads if "F.Cu" in x.layers or "B.Cu" in x.layers]
                if not smd:
                    continue
                pad = min(smd, key=lambda p: (p.pos[0] - 29) ** 2 + (p.pos[1] - 55) ** 2)
                if self._stitch_pad(pad, net, region, f"stitch-{net}-{gi}"):
                    self.report["stitched"].append(pad.label)
            self._rebuild()
            by_net_groups = defaultdict(list)
            for g in self.groups:
                pads = [x for x in g if x.kind == "pad" and x.net]
                if pads and len({x.net for x in pads}) == 1:
                    by_net_groups[next(iter(pads)).net].append(g)

    def _stitch_pad(self, pad, net, region, tag):
        px, py = pad.pos
        fp = next(f for f in children(self.board, "footprint") if fp_ref(f) == pad.ref)
        fx, fy, *ang = map(float, values(fp, "at"))
        # Prefer away from footprint centre.
        dx, dy = px - fx, py - fy
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        candidates = []
        for dist_mm in (0.50, 0.65, 0.80, 1.00, 1.20, 1.45, 1.70, 2.00, 2.40):
            for ang_off in (0, 35, -35, 70, -70, 110, -110, 180):
                a = math.radians(ang_off)
                ca, sa = math.cos(a), math.sin(a)
                rx, ry = ux * ca - uy * sa, ux * sa + uy * ca
                candidates.append((px + rx * dist_mm, py + ry * dist_mm))
        for vx, vy in candidates:
            if region == "outside_core" and CORE_POLY.contains(Point(vx, vy)):
                continue
            if isinstance(region, Polygon) and not region.contains(Point(vx, vy)):
                continue
            if not self.add_via(vx, vy, net, f"{tag}-{vx:.2f}-{vy:.2f}"):
                continue
            w = 0.15 if net == "GND" else width_for(net)
            if self.add_seg(px, py, vx, vy, w, "F.Cu", net, f"{tag}-stub"):
                return True
            # Via placed but stub failed: still useful if via overlaps pad.
            if math.hypot(vx - px, vy - py) < 0.35:
                return True
        return False

    def add_power_zones(self):
        extra = [
            ("VSYS", "F.Cu", 5, [(8, 76), (26, 76), (26, 91), (8, 91)]),
            ("VBUS", "F.Cu", 5, [(12, 94), (36, 94), (36, 108), (12, 108)]),
            ("VBAT", "F.Cu", 5, [(16, 76), (24, 76), (24, 84), (16, 84)]),
            ("SD_3V3", "F.Cu", 5, [(24, 4), (42, 4), (42, 16), (24, 16)]),
            # SoC 3V3 sits inside the CORE In2 cutout; stitch on F.Cu to C14.
            ("3V3", "F.Cu", 6, [(22.0, 50.0), (37.6, 50.0), (37.6, 58.0), (42.5, 58.0), (42.5, 62.2), (22.0, 62.2)]),
            ("3V3", "F.Cu", 6, [(3.0, 80.0), (24.2, 80.0), (24.2, 90.2), (15.5, 90.2), (15.5, 86.0), (3.0, 86.0)]),
            ("3V3", "F.Cu", 6, [(20.0, 76.0), (27.2, 76.0), (27.2, 80.2), (20.0, 80.2)]),
            ("CORE_0V93", "In2.Cu", 2, [(37.4, 63.0), (46.2, 63.0), (46.2, 71.2), (37.4, 71.2)]),
            ("DRAM_1V5", "B.Cu", 4, [(2.0, 82.0), (16.2, 82.0), (16.2, 100.0), (2.0, 100.0)]),
            ("DRAM_1V5", "F.Cu", 6, [(28.0, 59.0), (33.2, 59.0), (33.2, 65.0), (45.2, 65.0), (45.2, 71.2), (28.0, 71.2)]),
            ("VSYS", "F.Cu", 5, [(48.5, 34.0), (56.8, 34.0), (56.8, 88.0), (48.5, 88.0)]),
            ("VSYS", "F.Cu", 5, [(24.0, 76.0), (50.0, 76.0), (50.0, 82.0), (24.0, 82.0)]),
            ("VSYS", "F.Cu", 5, [(40.0, 34.0), (48.5, 34.0), (48.5, 48.0), (40.0, 48.0)]),
            ("VBUS", "F.Cu", 5, [(14.0, 80.0), (22.0, 80.0), (22.0, 96.0), (14.0, 96.0)]),
            ("1V8", "B.Cu", 3, [(44.0, 47.0), (48.2, 47.0), (48.2, 52.2), (44.0, 52.2)]),
            ("RTC_3V3", "B.Cu", 3, [(18.0, 78.0), (24.0, 78.0), (24.0, 88.0), (18.0, 88.0)]),
        ]
        existing = set()
        for z in children(self.board, "zone"):
            name = str(val(z, "net_name"))
            layer = str(val(z, "layer"))
            poly = child(z, "polygon")
            pts = ()
            if poly is not None:
                raw = child(poly, "pts")
                if raw is not None:
                    pts = tuple((round(float(p[1]), 2), round(float(p[2]), 2)) for p in raw[1:] if isinstance(p, list) and p and p[0] == "xy")
            existing.add((name, layer, pts))
        for net, layer, pri, pts in extra:
            key = (net, layer, tuple((round(x, 2), round(y, 2)) for x, y in pts))
            if key in existing or net not in self.ids:
                continue
            pts_s = " ".join(f"(xy {x:g} {y:g})" for x, y in pts)
            tag = f"zone-{net}-{layer}-{pts[0][0]:g}-{pts[0][1]:g}-minboot"
            text = f'''(zone (net {self.ids[net]}) (net_name "{net}") (layer "{layer}") (uuid "{gen.uid(tag)}") (hatch edge 0.5) (priority {pri})
\t\t(connect_pads (clearance .10)) (min_thickness .12) (fill yes (thermal_gap .25) (thermal_bridge_width .25))
\t\t(polygon (pts {pts_s}))
\t)'''
            self.board.append(loads(text))
            self.report["hygiene"].append(f"zone {net} {layer} {pts[0]}")

    def explicit_usb_pair(self):
        """Two parallel B.Cu skirts so DP does not consume the only corridor DM needs."""
        self._rebuild()
        pair = []
        for net, src_ref, dst_y in (("USB_DP", "U2", 48.2), ("USB_DM", "U2", 48.2)):
            src = None
            dst = None
            for it in self.items:
                xy = _xy(it.pos)
                if not xy or it.net != net or it.kind != "via":
                    continue
                if src_ref == "U2" and 46 < xy[1] < 52:
                    src = xy
                if xy[1] > 93:
                    dst = xy
            if src and dst:
                pair.append((net, src, dst))
        used = None
        for net, a, b in pair:
            w = USB_W
            ok = False
            for xjog in (50.6, 51.5, 49.6, 52.4, 16.2, 15.2, 17.2, 47.8):
                if used is not None and abs(xjog - used) < 0.55:
                    continue
                pieces = [
                    ("seg", (a[0], a[1], xjog, a[1], w, "B.Cu", net, net + f"-h1-{xjog}")),
                    ("seg", (xjog, a[1], xjog, b[1], w, "B.Cu", net, net + f"-v-{xjog}")),
                    ("seg", (xjog, b[1], b[0], b[1], w, "B.Cu", net, net + f"-h2-{xjog}")),
                ]
                if self.commit(pieces):
                    self.report["routes"][net + "_explicit"] = f"ok x={xjog}"
                    used = xjog
                    ok = True
                    break
            if not ok:
                self.report["routes"][net + "_explicit"] = "failed"

    def seed_short_links(self):
        """Local pad-to-pad links that a single foreign track otherwise seals."""
        self._rebuild()
        pads = {}
        for it in self.items:
            if it.kind == "pad" and it.net and it.ref:
                pads[(it.ref, it.pin)] = (_xy(it.pos), it.net)
        pairs = [
            (("R27", "2"), ("D5", "1")),
            (("R27", "1"), ("U2", "41")),
            (("U1", "39"), ("R5", "2")),
            (("R5", "2"), ("U2", "38")),
            (("U2", "31"), ("J3", "6")),
            (("U2", "40"), ("R21", "1")),
            (("U2", "6"), ("J5", "8")),
            (("J1", "A7"), ("U9", "3")),
            (("J1", "B7"), ("U9", "4")),
            (("J1", "A4"), ("U9", "5")),
            (("J1", "A9"), ("C32", "1")),
            (("C31", "1"), ("R22", "2")),
            (("R22", "2"), ("R23", "2")),
            (("R23", "2"), ("R24", "2")),
            (("R24", "2"), ("R25", "2")),
            (("R25", "2"), ("R26", "2")),
            (("SW1", "1"), ("R23", "1")),
            (("SW2", "1"), ("R24", "1")),
        ]
        for a, b in pairs:
            if a not in pads or b not in pads:
                continue
            (x1, y1), n1 = pads[a]
            (x2, y2), n2 = pads[b]
            if n1 != n2 or not x1:
                continue
            w = width_for(n1)
            if self._connect_pts(x1, y1, "F.Cu", x2, y2, "F.Cu", w, n1, f"seed-{a[0]}{a[1]}-{b[0]}{b[1]}"):
                self.report["routes"][f"{n1}_seed_{a[0]}"] = "ok"

    def explicit_long_hauls(self):
        """B.Cu skirts around the display keepout for USB and a few stubborn nets."""
        self._rebuild()
        vias = {}
        for it in self.items:
            if it.kind == "via" and it.net and _xy(it.pos):
                vias.setdefault(it.net, []).append(_xy(it.pos))
        pads = {}
        for it in self.items:
            if it.kind == "pad" and it.net and _xy(it.pos):
                pads.setdefault(it.net, []).append((it.ref, it.pin, _xy(it.pos)))

        def nearest(net, ref=None):
            pts = []
            if net in vias:
                pts.extend(("B.Cu", p) for p in vias[net])
            for r, pn, p in pads.get(net, []):
                if ref and r != ref:
                    continue
                pts.append(("F.Cu", p))
            return pts

        # USB pair: from SoC escape vias, skirt the display keepout, then south to U9.
        for net in ("USB_DP", "USB_DM"):
            srcs = [p for layer, p in nearest(net) if 45 < p[1] < 52]
            dsts = [p for layer, p in nearest(net) if p[1] > 94]
            if not srcs or not dsts:
                continue
            a, b = srcs[0], dsts[0]
            w = USB_W
            for xjog in (41.0, 42.2, 43.5, 45.0, 47.0, 39.0, 18.0, 16.0, 50.0):
                pieces = [
                    ("seg", (a[0], a[1], xjog, a[1], w, "B.Cu", net, net + f"-k1-{xjog}")),
                    ("seg", (xjog, a[1], xjog, b[1], w, "B.Cu", net, net + f"-k2-{xjog}")),
                    ("seg", (xjog, b[1], b[0], b[1], w, "B.Cu", net, net + f"-k3-{xjog}")),
                ]
                if self.commit(pieces):
                    self.report["routes"][net + "_explicit"] = f"ok x={xjog}"
                    break

        # VSYS to display-side boost: from PMIC island to U7/L4.
        vsys_src = [p for r, pn, p in pads.get("VSYS", []) if r in {"C38", "C41", "U1"}]
        vsys_dst = [p for r, pn, p in pads.get("VSYS", []) if r in {"C28", "U7", "L4"}]
        if vsys_src and vsys_dst:
            a, b = vsys_src[0], vsys_dst[0]
            xjog = 48.0
            w = PWR_W
            self.commit([
                ("seg", (a[0], a[1], xjog, a[1], w, "B.Cu", "VSYS", "vsys-k1")),
                ("seg", (xjog, a[1], xjog, b[1], w, "B.Cu", "VSYS", "vsys-k2")),
                ("seg", (xjog, b[1], b[0], b[1], w, "B.Cu", "VSYS", "vsys-k3")),
            ])

    def thermal_vias(self):
        for name, cx, cy, span in (("u2", 30.0, 56.0, 1.6), ("u1", 18.0, 85.0, 1.2)):
            n = 0
            for dx in (-span / 2, 0.0, span / 2):
                for dy in (-span / 2, 0.0, span / 2):
                    n += 1
                    self.add_via(cx + dx, cy + dy, "GND", f"thermal-{name}-{n}")

    def route_all(self):
        skip_trace = set(STITCH_POUR) | {"GND"}
        nets = [n for n in PRIORITY if n not in skip_trace]
        present = {str(n[2]) for n in children(self.board, "net") if len(n) > 2}
        extra = sorted(present - set(PRIORITY) - gen.DISPLAY_NETS - {""} - skip_trace - {"PMIC_PWROK"})
        extra = [n for n in extra if not n.startswith("unconnected-")]
        for net in nets + extra:
            if net in gen.DISPLAY_NETS and net != "LCD_3V3":
                continue
            self.route_net(net)

    def route_net(self, net):
        self._rebuild()
        groups = []
        for g in self.groups:
            pads = [x for x in g if x.kind == "pad" and x.net == net]
            if pads:
                groups.append(g)
        if len(groups) <= 1:
            self.report["routes"][net] = "already connected or single island"
            return
        width = width_for(net)
        guard = 0
        while len(groups) > 1 and guard < 80:
            guard += 1
            groups.sort(key=lambda g: len([x for x in g if x.kind == "pad"]))
            src = groups[0]
            best = None
            sx, sy = _centroid(src)
            for dst in groups[1:]:
                dx, dy = _centroid(dst)
                dist = math.hypot(dx - sx, dy - sy)
                if best is None or dist < best[0]:
                    best = (dist, dst)
            dst = best[1]
            joined = self._join_groups(net, src, dst, width)
            if not joined:
                for alt in groups[1:]:
                    if alt is dst:
                        continue
                    if self._join_groups(net, src, alt, width):
                        joined = True
                        break
            if joined:
                self._rebuild()
                groups = [g for g in self.groups if any(x.kind == "pad" and x.net == net for x in g)]
            else:
                self.report["failed"].append(net)
                self.report["routes"][net] = f"failed with {len(groups)} islands"
                return
        self.report["routes"][net] = "ok" if len(groups) <= 1 else f"{len(groups)} islands remain"

    def _join_groups(self, net, src, dst, width):
        starts = _anchors(src)
        goals = _anchors(dst)
        src_vias = [(xy[0], xy[1], "B.Cu") for x in src if x.kind == "via" and (xy := _xy(x.pos))]
        dst_vias = [(xy[0], xy[1], "B.Cu") for x in dst if x.kind == "via" and (xy := _xy(x.pos))]
        if src_vias and dst_vias:
            for lock in ("B.Cu", "F.Cu", None):
                s = [(x, y, lock or "B.Cu") for x, y, _ in src_vias[:6]] if lock else src_vias[:6]
                g = [(x, y, lock or "B.Cu") for x, y, _ in dst_vias[:6]] if lock else dst_vias[:6]
                path = self._astar(s, g, net, width, lock_layer=lock)
                if path and self._emit_path(path, net, width):
                    return True
        pairs = []
        for ax, ay, alayer in starts:
            for bx, by, blayer in goals:
                pairs.append((0 if alayer == blayer else 1, math.hypot(bx - ax, by - ay), ax, ay, alayer, bx, by, blayer))
        pairs.sort()
        for _mismatch, dist, ax, ay, alayer, bx, by, blayer in pairs[:48]:
            if self._connect_pts(ax, ay, alayer, bx, by, blayer, width, net, f"{net}-{ax:.1f}-{bx:.1f}"):
                return True
        path = self._astar(starts[:8], goals[:8], net, width)
        return bool(path and self._emit_path(path, net, width))

    def _snapshot(self):
        return len(self.board), len(self.items), self.report["added_tracks"], self.report["added_vias"]

    def _restore(self, snap, mark):
        nboard, nitems, nt, nv = snap
        # Copper is inserted just before the first zone; drop nodes added after `mark`.
        self.board[:] = [x for x in self.board if id(x) not in mark]
        self.items = self.items[:nitems]
        self.report["added_tracks"] = nt
        self.report["added_vias"] = nv

    def _connect_pts(self, x1, y1, l1, x2, y2, l2, width, net, tag):
        if l1 == l2:
            if self._manhattan(x1, y1, x2, y2, l1, width, net, tag):
                return True
            path = self._astar([(x1, y1, l1)], [(x2, y2, l2)], net, width)
            return bool(path and self._emit_path(path, net, width))
        offsets = ((0.9, 0), (-0.9, 0), (0, 0.9), (0, -0.9), (1.3, 0.7), (-1.3, 0.7), (1.3, -0.7), (-1.3, -0.7), (1.8, 0), (-1.8, 0))
        for ox, oy in offsets:
            vx, vy = x2 + ox, y2 + oy
            snap = self._snapshot()
            before = {id(x) for x in self.board}
            if not self.add_via(vx, vy, net, tag + "-via"):
                continue
            if self._manhattan(x1, y1, vx, vy, l1, width, net, tag):
                self.add_seg(vx, vy, x2, y2, width, l2, net, tag + "-stub")
                return True
            added = {id(x) for x in self.board} - before
            self._restore(snap, added)
        path = self._astar([(x1, y1, l1)], [(x2, y2, l2)], net, width)
        return bool(path and self._emit_path(path, net, width))

    def _manhattan(self, x1, y1, x2, y2, layer, width, net, tag):
        if math.hypot(x2 - x1, y2 - y1) < 1e-4:
            return True
        mids = [(x2, y1), (x1, y2)]
        for o in (0.6, -0.6, 1.2, -1.2, 2.0, -2.0, 3.0, -3.0, 4.5, -4.5, 6.5, -6.5, 9.0, -9.0):
            mids.append((x2, y1 + o))
            mids.append((x1 + o, y2))
            mids.append(((x1 + x2) / 2 + o, y1))
            mids.append((x1, (y1 + y2) / 2 + o))
            mids.append(((x1 + x2) / 2, (y1 + y2) / 2 + o))
        for i, (mx, my) in enumerate(mids):
            pieces = []
            if math.hypot(mx - x1, my - y1) > 1e-4:
                pieces.append(("seg", (x1, y1, mx, my, width, layer, net, f"{tag}-a{i}")))
            if math.hypot(x2 - mx, y2 - my) > 1e-4:
                pieces.append(("seg", (mx, my, x2, y2, width, layer, net, f"{tag}-b{i}")))
            if pieces and self.commit(pieces):
                return True
        # Three-segment U-jog in both axes so a single foreign track does not seal the pair.
        for o in (2.0, -2.0, 4.0, -4.0, 7.0, -7.0, 10.0, -10.0, 14.0, -14.0):
            for p1, p2 in (
                ((x1, y1 + o), (x2, y1 + o)),
                ((x1 + o, y1), (x1 + o, y2)),
            ):
                pieces = [
                    ("seg", (x1, y1, p1[0], p1[1], width, layer, net, tag + f"-u1{o}")),
                    ("seg", (p1[0], p1[1], p2[0], p2[1], width, layer, net, tag + f"-u2{o}")),
                    ("seg", (p2[0], p2[1], x2, y2, width, layer, net, tag + f"-u3{o}")),
                ]
                if self.commit(pieces):
                    return True
        return False

    def _astar(self, starts, goals, net, width, lock_layer=None):
        layers = ("F.Cu", "B.Cu")
        xmin, xmax, ymin, ymax = EDGE + 0.3, 58 - EDGE - 0.3, EDGE + 0.3, 110 - EDGE - 0.3
        nx = int((xmax - xmin) / GRID) + 1
        ny = int((ymax - ymin) / GRID) + 1
        blocked = self._raster(net, width, xmin, ymin, nx, ny)
        via_block = self._via_raster(net, xmin, ymin, nx, ny)

        def cell(x, y):
            return int(round((x - xmin) / GRID)), int(round((y - ymin) / GRID))

        def pos(ix, iy):
            return xmin + ix * GRID, ymin + iy * GRID

        goal_cells = set()
        for x, y, layer in goals:
            if lock_layer and layer != lock_layer:
                continue
            ix, iy = cell(x, y)
            li = 0 if layer != "B.Cu" else 1
            if 0 <= ix < nx and 0 <= iy < ny:
                blocked[li][iy][ix] = False
                goal_cells.add((ix, iy, li))
        if not goal_cells:
            return None
        heap = []
        seen = set()
        seq = 0
        for x, y, layer in starts:
            if lock_layer and layer != lock_layer:
                continue
            li = 0 if layer != "B.Cu" else 1
            ix, iy = cell(x, y)
            if not (0 <= ix < nx and 0 <= iy < ny):
                continue
            if 0 <= ix < nx and 0 <= iy < ny:
                blocked[li][iy][ix] = False
            heapq.heappush(heap, (0, seq, ix, iy, li, None))
            seq += 1
        parent = {}
        gx = sum(c[0] for c in goal_cells) / len(goal_cells)
        gy = sum(c[1] for c in goal_cells) / len(goal_cells)
        while heap:
            cost, _, ix, iy, li, prev = heapq.heappop(heap)
            key = (ix, iy, li)
            if key in seen:
                continue
            seen.add(key)
            parent[key] = prev
            if key in goal_cells or (ix, iy, li) in goal_cells:
                path = []
                cur = key
                while cur is not None:
                    path.append(cur)
                    cur = parent.get(cur)
                path.reverse()
                return [(pos(i, j)[0], pos(i, j)[1], layers[l]) for i, j, l in path]
            if len(seen) > 400000:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                jx, jy = ix + dx, iy + dy
                if not (0 <= jx < nx and 0 <= jy < ny):
                    continue
                if blocked[li][jy][jx]:
                    continue
                nkey = (jx, jy, li)
                if nkey in seen:
                    continue
                turn = 0.0
                if prev is not None:
                    pdx, pdy = ix - prev[0], iy - prev[1]
                    if (pdx, pdy) != (dx, dy):
                        turn = 0.6
                h = abs(jx - gx) + abs(jy - gy)
                heapq.heappush(heap, (cost + 1 + turn + h * 0.01, seq, jx, jy, li, key))
                seq += 1
            if lock_layer is None:
                other = 1 - li
                if not via_block[iy][ix] and not blocked[other][iy][ix]:
                    nkey = (ix, iy, other)
                    if nkey not in seen:
                        heapq.heappush(heap, (cost + 80, seq, ix, iy, other, key))
                        seq += 1
        return None

    def _raster(self, net, width, xmin, ymin, nx, ny):
        # Hole-to-copper (0.25) is tighter than copper-to-copper (0.09) around 0.40/0.20 vias.
        keep = max(CLEAR, HOLE_CU - (VIA - DRILL) / 2) + width / 2 + 0.04
        blocked = [[[False] * nx for _ in range(ny)] for _ in range(2)]
        layer_i = {"F.Cu": 0, "B.Cu": 1}
        for it in self.items:
            if it.net == net:
                continue
            layers = [layer_i[l] for l in it.layers if l in layer_i]
            if not layers:
                continue
            minx, miny, maxx, maxy = it.geom.bounds
            minx -= keep
            miny -= keep
            maxx += keep
            maxy += keep
            ix0 = max(0, int((minx - xmin) / GRID) - 1)
            iy0 = max(0, int((miny - ymin) / GRID) - 1)
            ix1 = min(nx - 1, int((maxx - xmin) / GRID) + 1)
            iy1 = min(ny - 1, int((maxy - ymin) / GRID) + 1)
            if ix0 > ix1 or iy0 > iy1:
                continue
            for iy in range(iy0, iy1 + 1):
                y = ymin + iy * GRID
                for ix in range(ix0, ix1 + 1):
                    x = xmin + ix * GRID
                    if it.geom.distance(Point((x, y))) <= keep:
                        for li in layers:
                            blocked[li][iy][ix] = True
        return blocked

    def _via_raster(self, net, xmin, ymin, nx, ny):
        block = [[False] * nx for _ in range(ny)]
        min_cc = DRILL + HOLE_HOLE
        min_cc2 = min_cc * min_cc
        for it in self.items:
            if it.hole is None:
                continue
            pos = it.pos
            if not (isinstance(pos, tuple) and len(pos) == 2 and isinstance(pos[0], (int, float))):
                pos = (it.geom.centroid.x, it.geom.centroid.y)
            hx, hy = pos
            rad = min_cc + GRID
            ix0 = max(0, int((hx - rad - xmin) / GRID) - 1)
            iy0 = max(0, int((hy - rad - ymin) / GRID) - 1)
            ix1 = min(nx - 1, int((hx + rad - xmin) / GRID) + 1)
            iy1 = min(ny - 1, int((hy + rad - ymin) / GRID) + 1)
            for iy in range(iy0, iy1 + 1):
                y = ymin + iy * GRID
                dy = y - hy
                for ix in range(ix0, ix1 + 1):
                    x = xmin + ix * GRID
                    dx = x - hx
                    if dx * dx + dy * dy < min_cc2:
                        block[iy][ix] = True
        return block

    def _emit_path(self, path, net, width):
        if not path:
            return False
        # Snap ends to the nearest same-net via so the track actually touches it.
        def snap(pt, end):
            x, y, layer = pt
            best = None
            for it in self.items:
                if it.kind != "via" or it.net != net:
                    continue
                xy = _xy(it.pos)
                if not xy:
                    continue
                d = math.hypot(xy[0] - x, xy[1] - y)
                if d < 0.80 and (best is None or d < best[0]):
                    best = (d, xy)
            if best:
                return (best[1][0], best[1][1], layer)
            return pt
        path = [snap(path[0], "start")] + list(path[1:-1]) + [snap(path[-1], "end")]
        merged = []
        for pt in path:
            if not merged:
                merged.append(pt)
                continue
            x0, y0, l0 = merged[-1]
            x1, y1, l1 = pt
            if l0 == l1 and merged[-1] is not None:
                if len(merged) >= 2:
                    x2, y2, l2 = merged[-2]
                    if l2 == l1 and ((x2 == x1 == x0) or (y2 == y1 == y0)):
                        merged[-1] = pt
                        continue
            merged.append(pt)
        pieces = []
        for (x1, y1, l1), (x2, y2, l2) in zip(merged, merged[1:]):
            if l1 != l2:
                reuse = any(
                    it.kind == "via" and it.net == net and _xy(it.pos) and math.hypot(_xy(it.pos)[0] - x1, _xy(it.pos)[1] - y1) < 0.80
                    for it in self.items
                )
                if not reuse:
                    pieces.append(("via", (x1, y1, net, f"ar-{net}-{x1:.2f}-{y1:.2f}")))
                continue
            pieces.append(("seg", (x1, y1, x2, y2, width, l1, net, f"ar-{net}-{x1:.2f}-{y1:.2f}")))
        return self.commit(pieces) if pieces else False


def _xy(pos):
    if not (isinstance(pos, tuple) and len(pos) == 2):
        return None
    if isinstance(pos[0], (int, float)) and isinstance(pos[1], (int, float)):
        return float(pos[0]), float(pos[1])
    return None


def _centroid(group):
    pts = [xy for x in group if (xy := _xy(x.pos))]
    if not pts:
        return 0.0, 0.0
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def _anchors(group):
    out = []
    for x in group:
        xy = _xy(x.pos)
        if not xy:
            continue
        if x.kind == "via":
            out.append((xy[0], xy[1], "B.Cu"))
            out.append((xy[0], xy[1], "F.Cu"))
        elif x.kind == "pad":
            layer = "F.Cu" if "F.Cu" in x.layers else ("B.Cu" if "B.Cu" in x.layers else "F.Cu")
            out.append((xy[0], xy[1], layer))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write", action="store_true")
    p.add_argument("--continue-routing", action="store_true", help="Do not restitch; only route remaining islands")
    p.add_argument("--nets", help="Comma-separated net names to route instead of the full minboot set")
    a = p.parse_args()
    board = load(BOARD)
    devs = {d.ref: d for d in gen.devices()}
    r = Router(board)
    r.hygiene(devs)
    if not a.continue_routing:
        r.add_power_zones()
        r.thermal_vias()
        r.stitch_planes()
    r.seed_short_links()
    r.explicit_usb_pair()
    if a.nets:
        for net in [n.strip() for n in a.nets.split(",") if n.strip()]:
            r.route_net(net)
    else:
        r.route_all()
    r.explicit_long_hauls()
    r._strip_zone_fills()
    seen = set()
    nfix = 0
    def repair_uuid(node):
        nonlocal nfix
        if not isinstance(node, list):
            return
        if node and node[0] == "uuid":
            old = str(node[1])
            if old in seen:
                new = gen.uid(f"minboot-dup-{old}-{nfix}")
                node[1] = Q(new)
                nfix += 1
                seen.add(new)
            else:
                seen.add(old)
            return
        for x in node:
            repair_uuid(x)
    repair_uuid(board)
    r.report["uuid_repairs"] = nfix
    geom = issues(board_items(board))
    r.report["static_geometry_issues"] = len(geom)
    r.report["geometry_sample"] = geom[:12]
    groups = connected_groups(board_items(board))
    islands = defaultdict(int)
    for g in groups:
        pads = [x for x in g if x.kind == "pad" and x.net]
        if pads:
            islands[next(iter({x.net for x in pads}))] += 1
    r.report["islands_excluding_zones"] = {n: c for n, c in sorted(islands.items()) if c > 1 and n not in gen.DISPLAY_NETS}
    out = ROOT / "verification" / "minboot_route_report.json"
    out.write_text(json.dumps(r.report, indent=2) + "\n")
    print(json.dumps({k: r.report[k] for k in ("moved", "added_tracks", "added_vias", "static_geometry_issues") if k in r.report}, indent=2))
    print("failed", r.report["failed"])
    print("islands", r.report["islands_excluding_zones"])
    print("Report:", out)
    if geom:
        print("Geometry issues remain; PCB not written" if not a.write else "WARNING: writing despite geometry issues")
        if not a.write:
            raise SystemExit(2)
    if a.write:
        dump(board, BOARD)
        print("Wrote", BOARD)
    else:
        print("Dry-run only. Re-run with --write to save the PCB.")


if __name__ == "__main__":
    main()
