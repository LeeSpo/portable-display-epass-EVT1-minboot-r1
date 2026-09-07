#!/usr/bin/env python3
"""DRC-aware WEB6 router. Appends copper; never re-serializes the whole PCB.

Uses Shapely geometry from v0_legacy tools. Via 0.60/0.30 mm. Not fab sign-off.
"""
from __future__ import annotations
import heapq, json, math, sys, time, uuid, uuid as uuidlib
from collections import defaultdict
from pathlib import Path

import shapely
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
V0 = ROOT.parent / "v0_legacy" / "tools"
sys.path.insert(0, str(V0))
from kicad_sexpr import load, children, val, values, Q  # noqa: E402
from geometry_audit import board_items, Item  # noqa: E402

BOARD = ROOT / "ak_display_38x64_PLACEMENT_ONLY.kicad_pcb"
REPORT = ROOT / "verification" / "routing_report.json"
NS = uuidlib.UUID("8c1f0b2e-6a7d-4c11-9f3a-2d5e7a91b0c4")

W, H, EDGE, CLEAR = 38.0, 64.0, 0.50, 0.127
VIA_D, VIA_DRILL = 0.60, 0.30
HOLE_HOLE = 0.25
SIG_W, HS_W, PWR_W, LX_W = 0.20, 0.127, 0.30, 0.40
STEP = 0.08
MAX_EXPAND = 70000
VIA_COST = 30.0
NX, NY = int(W / STEP) + 1, int(H / STEP) + 1
F, B = "F.Cu", "B.Cu"

POWER = {
    "VSYS", "VBUS", "VBAT", "3V3", "CORE_0V93", "DRAM_1V5", "1V8",
    "ELVDD", "ELVSS", "RTC_3V3", "LCD_3V3", "LCD_1V8", "SD_3V3",
    "SOC_LDO_1V8", "SOC_AVCC", "VMID", "VREF", "VRA1", "PMIC_BACKUP",
}
HS = {"DSI_D0P", "DSI_D0N", "DSI_CKP", "DSI_CKN", "USB_DP", "USB_DM"}
LX = {"LX_3V3", "LX_CORE", "LX_DRAM", "EL_SWP", "EL_SWN"}
PRIORITY = [
    "XIN", "XOUT", "LX_3V3", "LX_CORE", "LX_DRAM",
    "VREF", "VMID", "PMIC_BACKUP", "VRA1", "SOC_AVCC", "SOC_LDO_1V8",
    "EL_SWP", "EL_SWN", "EL_CT", "ELVDD", "ELVSS",
    "WAKE_CEXT", "WAKE_REXT", "WAKE_PULSE", "WAKE_PULSE_N", "WAKE_REQ_N",
    "DSI_D0P", "DSI_D0N", "DSI_CKP", "DSI_CKN",
    "USB_DP", "USB_DM", "USB_CC1", "USB_CC2",
    "VBUS", "VBAT", "VSYS",
    "NAND_CLK", "NAND_CS", "NAND_MISO", "NAND_MOSI", "NAND_HOLD", "NAND_WP",
    "SD_CLK", "SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3", "SD_DET",
    "SD_PWR_EN", "SD_PWR_GATE", "SD_3V3",
    "I2C0_SCL", "I2C0_SDA", "UART0_TX", "UART0_RX", "E907_TX", "E907_RX",
    "PMIC_SCL", "PMIC_SDA", "PMIC_IRQ_N", "PWRON_N",
    "ACCEL_INT_N", "RTC_INT_N", "RTC_EVI", "RTC_VBACKUP",
    "LCD_EN", "LCD_RST", "LCD_TE", "LCD_SWIRE", "LCD_1V8", "LCD_3V3",
    "ADC_KEYS", "KEY_UP", "KEY_DOWN", "KEY_OK", "KEY_BACK",
    "STATUS_LED", "STATUS_LED_A", "CHGLED_A", "CHGLED_N", "BAT_NTC",
    "CORE_0V93", "DRAM_1V5", "1V8", "3V3", "RTC_3V3",
]


def skip_net(n):
    return (not n) or n == "GND" or n.startswith("unconnected")


def width_for(net):
    if net in HS:
        return HS_W
    if net in LX:
        return LX_W
    if net in POWER:
        return PWR_W
    return SIG_W


def uid(name):
    return str(uuid.uuid5(NS, name))


def q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


class Router:
    def __init__(self, board):
        self.board = board
        self.ids = {str(n[2]): int(n[1]) for n in children(board, "net") if len(n) > 2 and str(n[2])}
        self.items = board_items(board)
        self.keep = self._keepouts()
        self.added = []  # raw sexpr lines
        self.report = {"routes": {}, "failed": [], "added_tracks": 0, "added_vias": 0, "notes": [],
                       "fabrication_released": False, "impedance_verified": False}
        self.via_xy = []
        self.fp = {}
        for it in self.items:
            if it.kind == "pad" and it.ref:
                self.fp.setdefault(it.ref, []).append(it)

    def _keepouts(self):
        geoms = [box(0, 0, W, EDGE), box(0, H - EDGE, W, H), box(0, 0, EDGE, H), box(W - EDGE, 0, W, H)]
        for cx, cy in ((3, 3), (35, 3), (3, 61), (35, 61)):
            geoms.append(Point(cx, cy).buffer(2.50, quad_segs=24))
        return unary_union(geoms)

    def _rebuild_tree(self):
        self.tree = STRtree([i.geom for i in self.items])

    def _ok(self, geom, layers, net, hole=None):
        if self.keep.distance(geom) < 1e-6:
            return False
        hits = self.tree.query(geom.buffer(CLEAR))
        for j in hits:
            it = self.items[int(j)]
            same = it.net == net and net
            if not same and it.layers & layers:
                if it.geom.distance(geom) < CLEAR - 1e-6:
                    return False
            if hole is not None and it.hole is not None:
                if hole.distance(it.hole) < HOLE_HOLE - 1e-6:
                    return False
            if not same:
                if hole is not None and it.layers and hole.distance(it.geom) < 0.25 - 1e-6:
                    return False
                if it.hole is not None and layers and it.hole.distance(geom) < 0.25 - 1e-6:
                    return False
        return True

    def add_seg(self, x1, y1, x2, y2, width, layer, net):
        if math.hypot(x2 - x1, y2 - y1) < 1e-4:
            return True
        geom = LineString(((x1, y1), (x2, y2))).buffer(width / 2, quad_segs=12)
        layers = frozenset((layer,))
        if not self._ok(geom, layers, net):
            return False
        tag = f"seg-{net}-{x1:.4f}-{y1:.4f}-{x2:.4f}-{y2:.4f}-{layer}"
        line = (f'  (segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) '
                f'(width {width:.3f}) (layer {q(layer)}) (net {self.ids[net]}) '
                f'(uuid {q(uid(tag))}))')
        node = ["segment"]
        item = Item("track", net, layers, geom, node, tag, pos=((x1, y1), (x2, y2)))
        self.items.append(item)
        self.added.append(line)
        self.report["added_tracks"] += 1
        self._rebuild_tree()
        return True

    def add_via(self, x, y, net):
        if not (EDGE + VIA_D / 2 <= x <= W - EDGE - VIA_D / 2):
            return False
        if not (EDGE + VIA_D / 2 <= y <= H - EDGE - VIA_D / 2):
            return False
        for vx, vy in self.via_xy:
            if math.hypot(x - vx, y - vy) < 0.85:
                return False
        geom = Point((x, y)).buffer(VIA_D / 2, quad_segs=16)
        hole = Point((x, y)).buffer(VIA_DRILL / 2, quad_segs=16)
        layers = frozenset((F, B, "In1.Cu", "In2.Cu"))
        if not self._ok(geom, layers, net, hole):
            return False
        tag = f"via-{net}-{x:.4f}-{y:.4f}"
        line = (f'  (via (at {x:.4f} {y:.4f}) (size {VIA_D:.2f}) (drill {VIA_DRILL:.2f}) '
                f'(layers "F.Cu" "B.Cu") (net {self.ids[net]}) (uuid {q(uid(tag))}))')
        item = Item("via", net, layers, geom, ["via"], tag, hole, pos=(x, y))
        self.items.append(item)
        self.added.append(line)
        self.via_xy.append((x, y))
        self.report["added_vias"] += 1
        self._rebuild_tree()
        return True

    def commit_xy(self, pts, width, net):
        """pts: (x,y,layer). Layer change inserts a via at the shared point."""
        if len(pts) < 2:
            return False
        staged = []
        saved_items = list(self.items)
        saved_added = list(self.added)
        saved_vias = list(self.via_xy)
        saved_tr, saved_via_n = self.report["added_tracks"], self.report["added_vias"]
        ok = True
        for a, b in zip(pts, pts[1:]):
            if a[2] != b[2]:
                if not self.add_via(a[0], a[1], net):
                    if not self.add_via(b[0], b[1], net):
                        ok = False
                        break
                continue
            if not self.add_seg(a[0], a[1], b[0], b[1], width, a[2], net):
                ok = False
                break
        if not ok:
            self.items = saved_items
            self.added = saved_added
            self.via_xy = saved_vias
            self.report["added_tracks"] = saved_tr
            self.report["added_vias"] = saved_via_n
            self._rebuild_tree()
            return False
        return True

    def manhattan(self, x1, y1, x2, y2, layer, width, net):
        cands = []
        if abs(x1 - x2) < 1e-4 or abs(y1 - y2) < 1e-4:
            cands.append([(x1, y1, layer), (x2, y2, layer)])
        else:
            cands.append([(x1, y1, layer), (x2, y1, layer), (x2, y2, layer)])
            cands.append([(x1, y1, layer), (x1, y2, layer), (x2, y2, layer)])
        for pts in cands:
            if self.commit_xy(pts, width, net):
                return True
        return False

    def _obstacles(self, net, width, layer):
        buf = width / 2 + CLEAR
        geoms = [self.keep.buffer(width / 2)]
        for it in self.items:
            if it.net == net:
                continue
            if layer not in it.layers:
                continue
            geoms.append(it.geom.buffer(buf))
        return unary_union(geoms)

    def astar(self, x1, y1, l1, x2, y2, l2, width, net):
        obs = {F: self._obstacles(net, width, F), B: self._obstacles(net, width, B)}
        for k in obs:
            shapely.prepare(obs[k])

        def blocked(x, y, layer):
            return shapely.intersects_xy(obs[layer], x, y)

        def cell(x, y):
            return int(round(x / STEP)), int(round(y / STEP))

        def xy(ix, iy):
            return ix * STEP, iy * STEP

        s = (*cell(x1, y1), l1)
        t = (*cell(x2, y2), l2)

        def h(st):
            return abs(st[0] - t[0]) + abs(st[1] - t[1]) + (0 if st[2] == t[2] else VIA_COST)

        dist = {s: 0.0}
        parent = {}
        heap = [(h(s), 0.0, s)]
        done = set()
        found = None
        expands = 0
        nbrs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        while heap and expands < MAX_EXPAND:
            _, cost, st = heapq.heappop(heap)
            if st in done:
                continue
            done.add(st)
            expands += 1
            if st[0] == t[0] and st[1] == t[1] and st[2] == t[2]:
                found = st
                break
            ix, iy, ly = st
            for dx, dy in nbrs:
                nx, ny = ix + dx, iy + dy
                x, y = xy(nx, ny)
                if not (EDGE <= x <= W - EDGE and EDGE <= y <= H - EDGE):
                    continue
                if blocked(x, y, ly):
                    continue
                nst = (nx, ny, ly)
                nc = cost + 1.0
                if nc >= dist.get(nst, 1e18):
                    continue
                dist[nst] = nc
                parent[nst] = st
                heapq.heappush(heap, (nc + h(nst), nc, nst))
            if (ix + iy) % 2 == 0:
                x, y = xy(ix, iy)
                nst = (ix, iy, B if ly == F else F)
                if nst not in done and not blocked(x, y, nst[2]):
                    nc = cost + VIA_COST
                    if nc < dist.get(nst, 1e18):
                        dist[nst] = nc
                        parent[nst] = st
                        heapq.heappush(heap, (nc + h(nst), nc, nst))
        if found is None:
            return False
        cells = [found]
        while cells[-1] in parent:
            cells.append(parent[cells[-1]])
        cells.reverse()
        pts = [(x1, y1, l1)]
        for ix, iy, ly in cells:
            x, y = xy(ix, iy)
            pts.append((x, y, ly))
        pts.append((x2, y2, l2))
        merged = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - merged[-1][0]) < 1e-6 and abs(p[1] - merged[-1][1]) < 1e-6 and p[2] == merged[-1][2]:
                continue
            merged.append(p)
        return self.commit_xy(merged, width, net)

    def connect(self, a, b, net, width):
        if self.manhattan(a[0], a[1], b[0], b[1], F, width, net):
            return True
        if self.astar(a[0], a[1], F, b[0], b[1], F, width, net):
            return True
        if self.astar(a[0], a[1], F, b[0], b[1], B, width, net):
            return True
        if self.astar(a[0], a[1], B, b[0], b[1], B, width, net):
            return True
        return False

    def route_net(self, net):
        pads = [i for i in self.items if i.kind == "pad" and i.net == net]
        if len(pads) < 2 or net not in self.ids:
            return True
        width = width_for(net)
        parent = list(range(len(pads)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        edges = []
        for i, a in enumerate(pads):
            for j in range(i + 1, len(pads)):
                b = pads[j]
                d = math.hypot(a.pos[0] - b.pos[0], a.pos[1] - b.pos[1])
                edges.append((d, i, j))
        edges.sort()
        need = len(pads) - 1
        got = 0
        fails = 0
        limit = 28 if net in POWER or len(pads) > 8 else 10
        for d, i, j in edges:
            if find(i) == find(j):
                continue
            a, b = pads[i], pads[j]
            if self.connect(a.pos, b.pos, net, width):
                parent[find(i)] = find(j)
                got += 1
                if got >= need:
                    break
            else:
                fails += 1
                if fails > limit:
                    break
        islands = len({find(i) for i in range(len(pads))})
        self.report["routes"][net] = {"pads": len(pads), "islands": islands, "ok": islands == 1, "width": width}
        if islands != 1:
            self.report["failed"].append(net)
            return False
        return True

    def route_mipi(self):
        specs = [
            ("DSI_D0N", [(18.875, 32.750), (18.875, 38.20), (19.900, 38.20), (19.900, 39.935)]),
            ("DSI_D0P", [(19.225, 32.750), (19.225, 41.20), (19.600, 41.20), (19.600, 43.000)]),
            ("DSI_CKN", [(20.275, 32.750), (20.275, 38.20), (21.100, 38.20), (21.100, 39.935)]),
            ("DSI_CKP", [(20.625, 32.750), (20.625, 41.20), (20.800, 41.20), (20.800, 43.000)]),
        ]
        for net, xy in specs:
            pts = [(x, y, F) for x, y in xy]
            ok = self.commit_xy(pts, HS_W, net)
            if not ok:
                self.route_net(net)
            else:
                self.report["routes"][net] = {"ok": True, "style": "mipi-explicit", "width": HS_W}

    def stitch_gnd(self):
        gnd_pads = [i for i in self.items if i.kind == "pad" and i.net == "GND"]
        if not gnd_pads:
            return
        # EPAD vias
        for x, y in ((17.1, 27.1), (18.9, 27.1), (17.1, 28.9), (18.9, 28.9), (25.0, 53.0), (7.5, 48.7)):
            self.add_via(x, y, "GND")
        n = 0
        for x in (8.0, 12.0, 16.0, 22.0, 26.0, 30.0):
            for y in (11.0, 18.0, 26.0, 35.0, 41.0, 50.0):
                if self.add_via(x, y, "GND"):
                    n += 1
        self.report["notes"].append(f"gnd vias extra {n}")

    def write(self):
        text = BOARD.read_text(encoding="utf-8")
        text = text.rstrip()
        if not text.endswith(")"):
            raise SystemExit("board file does not end with )")
        body = "\n".join(self.added)
        BOARD.write_text(text[:-1] + "\n" + body + "\n)\n", encoding="utf-8")


def net_order(r):
    names = set()
    for it in r.items:
        if it.kind == "pad" and not skip_net(it.net):
            names.add(it.net)
    rank = {n: i for i, n in enumerate(PRIORITY)}
    return sorted(names, key=lambda n: (rank.get(n, 1000), n))


def main():
    print("load", BOARD, flush=True)
    board = load(BOARD)
    r = Router(board)
    r._rebuild_tree()
    print("pads", sum(1 for i in r.items if i.kind == "pad"), "nets", len(r.ids), flush=True)
    print("MIPI", flush=True)
    r.route_mipi()
    done = {n for n, v in r.report["routes"].items() if v.get("ok")}
    names = [n for n in net_order(r) if n not in done]
    t0 = time.time()
    for i, net in enumerate(names, 1):
        t1 = time.time()
        pads = sum(1 for it in r.items if it.kind == "pad" and it.net == net)
        print(f"[{i}/{len(names)}] {net} pads={pads}", flush=True)
        r.route_net(net)
        rec = r.report["routes"].get(net, {})
        print(f"    ok={rec.get('ok')} islands={rec.get('islands')} {time.time()-t1:.2f}s", flush=True)
    print(f"nets {time.time()-t0:.1f}s", flush=True)
    r.stitch_gnd()
    r.write()
    r.report["ok_nets"] = sum(1 for v in r.report["routes"].values() if v.get("ok"))
    r.report["failed_count"] = len(r.report["failed"])
    r.report["failed"] = sorted(set(r.report["failed"]))
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(r.report, indent=2) + "\n")
    print(json.dumps({k: r.report[k] for k in ("added_tracks", "added_vias", "ok_nets", "failed_count", "failed")}, indent=2))
    return 0 if r.report["failed_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
