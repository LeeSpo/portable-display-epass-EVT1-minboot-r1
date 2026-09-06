#!/usr/bin/env python3
"""Display-island layout relax study (KiCad 9 pcbnew).

Opens a SoC↔J4 corridor by moving passives to west/east flanks (not into
sensor/KEY copper north of J4). Re-routes MIPI/GPIO/EL short.

Idempotent: restores verification/*.pre_layout_relax.bak when present.
Does not touch fabrication_released.
"""
from __future__ import annotations

import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

import pcbnew

PROJ = Path(__file__).resolve().parents[1]
PCB = PROJ / "portable_display_epass.kicad_pcb"
BAK = PROJ / "verification" / "portable_display_epass.kicad_pcb.pre_layout_relax.bak"
DOC = PROJ / "docs" / "DISPLAY_LAYOUT_RELAX.md"
METRICS = PROJ / "verification" / "layout_relax_metrics.json"

DISPLAY_NETS = {
    "LCD_EN", "LCD_RST", "LCD_TE", "LCD_TE1", "LCD_SWIRE",
    "LCD_3V3", "LCD_1V8",
    "DSI_D0P", "DSI_D0N", "DSI_CKP", "DSI_CKN",
    "ELVDD", "ELVSS", "EL_SWP", "EL_SWN", "EL_CT",
}

# Old EL island only (do not wipe board VSYS spine)
VSYS_CLEAR = (39.0, 24.0, 54.5, 36.5)
# Old R29/C4x island between J4 and U2 — purge 1V8 fanouts that targeted them
OLD_VCI_BOX = (24.0, 40.5, 36.5, 47.0)

# Dedicated study channels — delete ANY copper inside so display can run clean.
# Collateral nets are listed in the status doc for later restitch.
CHANNELS = [
    (26.2, 38.0, 30.2, 51.2),   # MIPI strip SoC→J4
    (22.4, 37.0, 24.2, 54.0),   # west GPIO / LCD_EN riser
    (13.5, 43.4, 48.5, 44.8),   # LCD_EN east-west to U8/U10
    (23.5, 38.6, 48.0, 39.8),   # EL bus under J4 south edge
]


def mm(x: float) -> int:
    return int(round(x * 1_000_000))


def fmm(v: int) -> float:
    return v / 1_000_000.0


def ensure(b, n):
    net = b.FindNet(n)
    if net is None or net.GetNetCode() == 0:
        net = pcbnew.NETINFO_ITEM(b, n)
        b.Add(net)
    return net


def pad_xy(fp, num: str):
    for p in fp.Pads():
        if p.GetNumber() == str(num):
            return fmm(p.GetPosition().x), fmm(p.GetPosition().y)
    raise KeyError(f"{fp.GetReference()}.{num}")


def move_fp(b, ref: str, x: float, y: float, rot: float | None = None):
    fp = b.FindFootprintByReference(ref)
    if fp is None:
        raise RuntimeError(f"missing {ref}")
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    if rot is not None:
        fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
    return fp


def add_track(b, a, c, width, net, layer=pcbnew.F_Cu):
    if abs(a[0] - c[0]) < 1e-6 and abs(a[1] - c[1]) < 1e-6:
        return None
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
    t.SetWidth(mm(width))
    t.SetLayer(layer)
    t.SetNet(net)
    b.Add(t)
    return t


def add_via(b, x, y, net, drill=0.2, width=0.4):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetDrill(mm(drill))
    for lyr in (pcbnew.F_Cu, pcbnew.B_Cu):
        try:
            v.SetWidth(lyr, mm(width))
        except Exception:
            pass
    try:
        v.SetNet(net)
    except Exception:
        v.SetNetCode(net.GetNetCode())
    b.Add(v)
    return v


def manhattan(b, a, c, width, net, layer=pcbnew.F_Cu, first="y"):
    if abs(a[0] - c[0]) < 1e-6 or abs(a[1] - c[1]) < 1e-6:
        add_track(b, a, c, width, net, layer)
        return
    mid = (a[0], c[1]) if first == "y" else (c[0], a[1])
    add_track(b, a, mid, width, net, layer)
    add_track(b, mid, c, width, net, layer)


def in_box(x, y, box):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


def delete_copper(b):
    to_del = []
    for t in list(b.GetTracks()):
        n = t.GetNetname()
        if t.Type() == pcbnew.PCB_VIA_T:
            pts = [(fmm(t.GetPosition().x), fmm(t.GetPosition().y))]
        else:
            pts = [
                (fmm(t.GetStart().x), fmm(t.GetStart().y)),
                (fmm(t.GetEnd().x), fmm(t.GetEnd().y)),
            ]
        if n in DISPLAY_NETS:
            to_del.append(t)
            continue
        if n == "VSYS" and all(in_box(x, y, VSYS_CLEAR) for x, y in pts):
            to_del.append(t)
            continue
        # old 1V8 tails into former R29 pocket
        if n == "1V8" and all(in_box(x, y, OLD_VCI_BOX) for x, y in pts):
            to_del.append(t)
            continue
    for t in to_del:
        b.Delete(t)
    return len(to_del)


def clear_box_nets(b, box, nets):
    """Delete any track/via of given nets fully inside box (collision scrub)."""
    to_del = []
    for t in list(b.GetTracks()):
        if t.GetNetname() not in nets:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            pts = [(fmm(t.GetPosition().x), fmm(t.GetPosition().y))]
        else:
            pts = [
                (fmm(t.GetStart().x), fmm(t.GetStart().y)),
                (fmm(t.GetEnd().x), fmm(t.GetEnd().y)),
            ]
        if all(in_box(x, y, box) for x, y in pts):
            to_del.append(t)
    for t in to_del:
        b.Delete(t)
    return len(to_del)


def clear_channels(b):
    """Delete all tracks/vias fully inside study channels; return collateral net counts."""
    from collections import Counter
    hit = Counter()
    to_del = []
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            pts = [(fmm(t.GetPosition().x), fmm(t.GetPosition().y))]
        else:
            pts = [
                (fmm(t.GetStart().x), fmm(t.GetStart().y)),
                (fmm(t.GetEnd().x), fmm(t.GetEnd().y)),
            ]
        for box in CHANNELS:
            if all(in_box(x, y, box) for x, y in pts):
                hit[t.GetNetname()] += 1
                to_del.append(t)
                break
    for t in to_del:
        b.Delete(t)
    return dict(hit), len(to_del)


def u2_courtyard(b):
    u2 = b.FindFootprintByReference("U2")
    xs = [fmm(p.GetPosition().x) for p in u2.Pads()]
    ys = [fmm(p.GetPosition().y) for p in u2.Pads()]
    return min(xs) - 0.5, min(ys) - 0.5, max(xs) + 0.5, max(ys) + 0.5


def metrics(b, label="", do_fill=True):
    net_len = defaultdict(float)
    net_vias = defaultdict(int)
    net_layers = defaultdict(set)
    for t in b.GetTracks():
        n = t.GetNetname()
        if n not in DISPLAY_NETS and n != "VSYS":
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            net_vias[n] += 1
        else:
            net_len[n] += fmm(t.GetLength())
            net_layers[n].add(b.GetLayerName(t.GetLayer()))
    cx0, cy0, cx1, cy1 = u2_courtyard(b)
    fcu = 0
    fcu_disp = 0
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T or t.GetLayer() != pcbnew.F_Cu:
            continue
        mx = (fmm(t.GetStart().x) + fmm(t.GetEnd().x)) / 2
        my = (fmm(t.GetStart().y) + fmm(t.GetEnd().y)) / 2
        if cx0 <= mx <= cx1 and cy0 <= my <= cy1:
            fcu += 1
            if t.GetNetname() in DISPLAY_NETS:
                fcu_disp += 1
    placements = {}
    for ref in [
        "J4", "U10", "U8", "L5", "L6", "R29", "R31",
        "C42", "C43", "C44", "C45", "C29",
        "C46", "C47", "C48", "C49", "C50", "C51", "U2", "J5",
    ]:
        fp = b.FindFootprintByReference(ref)
        if fp:
            placements[ref] = (
                round(fmm(fp.GetPosition().x), 2),
                round(fmm(fp.GetPosition().y), 2),
                round(fp.GetOrientationDegrees(), 1),
            )
    unconn = -1
    if do_fill:
        try:
            filler = pcbnew.ZONE_FILLER(b)
            filler.Fill(b.Zones())
        except Exception as e:
            print("zone fill warn", e)
        b.BuildConnectivity()
        try:
            unconn = b.GetConnectivity().GetUnconnectedCount(True)
        except Exception:
            unconn = -1
    # LCD_EN path estimate U2 → U10 (min manhattan via junction)
    try:
        u2 = b.FindFootprintByReference("U2")
        u10 = b.FindFootprintByReference("U10")
        a = pad_xy(u2, "4")
        c = pad_xy(u10, "7")
        en_path = abs(a[0] - c[0]) + abs(a[1] - c[1])
    except Exception:
        en_path = -1
    return {
        "label": label,
        "placements": placements,
        "lengths": {k: round(net_len.get(k, 0.0), 3) for k in sorted(DISPLAY_NETS)},
        "vias": {k: net_vias.get(k, 0) for k in sorted(DISPLAY_NETS)},
        "layers": {k: sorted(v) for k, v in net_layers.items()},
        "fcu_under_u2": fcu,
        "fcu_under_u2_display": fcu_disp,
        "unconnected": unconn,
        "lcd_en_u2_u10_manhattan": round(en_path, 3),
        "tracks": sum(1 for t in b.GetTracks() if t.Type() != pcbnew.PCB_VIA_T),
        "via_count": sum(1 for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T),
    }


def place_island(b):
    # Keep J4 near original — mild north shift only (avoid KEY_UP @ y≈28)
    move_fp(b, "J4", 30.0, 37.0, 0.0)

    # U10 EL cluster into empty east flank (y≈44), closer to SoC for short LCD_EN
    move_fp(b, "U10", 40.0, 44.0, 0.0)
    move_fp(b, "L5", 35.5, 42.0, 0.0)
    move_fp(b, "L6", 44.5, 42.0, 0.0)
    move_fp(b, "C46", 40.0, 39.5, 0.0)
    move_fp(b, "C47", 43.0, 39.5, 0.0)
    move_fp(b, "C48", 36.0, 45.5, 90.0)
    move_fp(b, "C49", 44.0, 45.5, 90.0)
    move_fp(b, "C50", 46.5, 47.5, 90.0)
    move_fp(b, "C51", 42.5, 48.0, 0.0)

    # VCI/VDDIO/load switch into empty west flank (out of MIPI corridor)
    move_fp(b, "U8", 19.0, 45.5, 0.0)
    move_fp(b, "C29", 15.5, 48.0, 0.0)
    move_fp(b, "C42", 16.5, 45.5, 90.0)
    move_fp(b, "C43", 17.5, 45.5, 90.0)
    move_fp(b, "C44", 18.0, 47.5, 90.0)
    move_fp(b, "C45", 20.0, 47.5, 90.0)
    move_fp(b, "R29", 22.5, 47.5, 0.0)
    move_fp(b, "R31", 22.5, 44.0, 0.0)


def route_el_island(b):
    u10 = b.FindFootprintByReference("U10")
    l5 = b.FindFootprintByReference("L5")
    l6 = b.FindFootprintByReference("L6")
    c46 = b.FindFootprintByReference("C46")
    c47 = b.FindFootprintByReference("C47")
    c48 = b.FindFootprintByReference("C48")
    c49 = b.FindFootprintByReference("C49")
    c50 = b.FindFootprintByReference("C50")
    c51 = b.FindFootprintByReference("C51")
    j4 = b.FindFootprintByReference("J4")

    n_swp, n_swn = ensure(b, "EL_SWP"), ensure(b, "EL_SWN")
    n_vdd, n_vss = ensure(b, "ELVDD"), ensure(b, "ELVSS")
    n_ct, n_vsys = ensure(b, "EL_CT"), ensure(b, "VSYS")
    n_gnd = ensure(b, "GND")

    add_track(b, pad_xy(l5, "2"), pad_xy(u10, "1"), 0.25, n_swp)
    add_track(b, pad_xy(u10, "10"), pad_xy(l6, "1"), 0.25, n_swn)

    add_track(b, pad_xy(l5, "1"), pad_xy(c46, "1"), 0.25, n_vsys)
    manhattan(b, pad_xy(c46, "1"), pad_xy(c47, "1"), 0.25, n_vsys, first="x")
    manhattan(b, pad_xy(c47, "1"), pad_xy(u10, "12"), 0.25, n_vsys, first="y")
    add_track(b, pad_xy(u10, "12"), pad_xy(u10, "11"), 0.25, n_vsys)

    # VSYS stitch on B.Cu to known spine via near U2 east (35.55, 53.05)
    vx, vy = pad_xy(u10, "11")
    stitch = (vx + 1.3, vy)
    add_track(b, (vx, vy), stitch, 0.25, n_vsys)
    add_via(b, *stitch, n_vsys)
    # stay east of main digital B.Cu: x=48 bus south then west
    manhattan(b, stitch, (42.0, 53.05), 0.25, n_vsys, pcbnew.B_Cu, first="y")
    add_track(b, (42.0, 53.05), (35.55, 53.05), 0.25, n_vsys, pcbnew.B_Cu)
    add_via(b, 35.55, 53.05, n_vsys)

    add_track(b, pad_xy(u10, "3"), pad_xy(u10, "4"), 0.25, n_vdd)
    manhattan(b, pad_xy(u10, "3"), pad_xy(c48, "1"), 0.25, n_vdd, first="x")
    manhattan(b, pad_xy(u10, "9"), pad_xy(c49, "1"), 0.25, n_vss, first="x")
    manhattan(b, pad_xy(c49, "1"), pad_xy(c50, "1"), 0.25, n_vss, first="y")
    manhattan(b, pad_xy(u10, "8"), pad_xy(c51, "1"), 0.15, n_ct, first="y")

    # EL to J4: B.Cu along y=39.2 (just south of J4), east side entry
    bus_y = 39.2
    for jpad, nobj, src in [
        ("7", n_vdd, pad_xy(u10, "4")),
        ("3", n_vss, pad_xy(u10, "9")),
    ]:
        jx, jy = pad_xy(j4, jpad)
        stub = (jx, jy + 0.85)
        add_track(b, (jx, jy), stub, 0.25, nobj)
        add_via(b, *stub, nobj)
        sx, sy = src
        gather = (sx, bus_y)
        add_track(b, (sx, sy), gather, 0.25, nobj)
        add_via(b, *gather, nobj)
        manhattan(b, gather, stub, 0.25, nobj, pcbnew.B_Cu, first="x")

    for a, c, nobj in [("6", "7", n_vdd), ("4", "3", n_vss)]:
        manhattan(b, pad_xy(j4, a), pad_xy(j4, c), 0.25, nobj, first="y")

    add_via(b, *pad_xy(u10, "13"), n_gnd)
    for fp, pn, dx, dy in [
        (l6, "2", 1.0, 0.0),
        (c46, "2", 0.0, -0.9),
        (c47, "2", 0.0, -0.9),
        (c48, "2", -0.9, 0.0),
        (c49, "2", 0.0, 0.9),
        (c50, "2", 1.0, 0.0),
        (c51, "2", 0.0, 0.9),
    ]:
        x, y = pad_xy(fp, pn)
        add_track(b, (x, y), (x + dx, y + dy), 0.2, n_gnd)
        add_via(b, x + dx, y + dy, n_gnd)
    for pn in ("2", "5", "6"):
        x, y = pad_xy(u10, pn)
        add_track(b, (x, y), (x - 1.0, y), 0.25, n_gnd)
        add_via(b, x - 1.0, y, n_gnd)


def route_vci_vddio(b):
    j4 = b.FindFootprintByReference("J4")
    u8 = b.FindFootprintByReference("U8")
    c29 = b.FindFootprintByReference("C29")
    c42 = b.FindFootprintByReference("C42")
    c43 = b.FindFootprintByReference("C43")
    c44 = b.FindFootprintByReference("C44")
    c45 = b.FindFootprintByReference("C45")
    r29 = b.FindFootprintByReference("R29")
    r31 = b.FindFootprintByReference("R31")

    n3 = ensure(b, "LCD_3V3")
    n18 = ensure(b, "LCD_1V8")
    n1v8 = ensure(b, "1V8")
    n3v3 = ensure(b, "3V3")
    n_gnd = ensure(b, "GND")
    n_sw = ensure(b, "LCD_SWIRE")

    # Local west island
    manhattan(b, pad_xy(u8, "6"), pad_xy(c42, "1"), 0.2, n3, first="x")
    add_track(b, pad_xy(c42, "1"), pad_xy(c43, "1"), 0.2, n3)
    manhattan(b, pad_xy(c43, "1"), pad_xy(c29, "1"), 0.2, n3, first="y")
    # To J4.9 on B.Cu to cross under corridor without fighting F.Cu MIPI
    jx, jy = pad_xy(j4, "9")
    cx, cy = pad_xy(c42, "1")
    add_track(b, (cx, cy), (cx, cy + 0.7), 0.2, n3)
    add_via(b, cx, cy + 0.7, n3)
    add_track(b, (jx, jy), (jx - 0.8, jy), 0.2, n3)
    add_via(b, jx - 0.8, jy, n3)
    manhattan(b, (cx, cy + 0.7), (jx - 0.8, jy), 0.2, n3, pcbnew.B_Cu, first="x")

    x, y = pad_xy(u8, "1")
    add_track(b, (x, y), (x - 0.8, y), 0.2, n3v3)
    add_via(b, x - 0.8, y, n3v3)

    add_track(b, pad_xy(c44, "1"), pad_xy(c45, "1"), 0.2, n18)
    manhattan(b, pad_xy(r29, "2"), pad_xy(c45, "1"), 0.2, n18, first="x")
    jx, jy = pad_xy(j4, "11")
    cx, cy = pad_xy(c44, "1")
    add_track(b, (cx, cy), (cx, cy + 0.7), 0.2, n18)
    add_via(b, cx, cy + 0.7, n18)
    add_track(b, (jx, jy), (jx - 0.8, jy), 0.2, n18)
    add_via(b, jx - 0.8, jy, n18)
    manhattan(b, (cx, cy + 0.7), (jx - 0.8, jy), 0.2, n18, pcbnew.B_Cu, first="x")

    x, y = pad_xy(r29, "1")
    # Stitch to existing 1V8 spine remnant near (34.05, 48.15) on F.Cu
    add_track(b, (x, y), (x, 48.15), 0.15, n1v8)
    add_track(b, (x, 48.15), (34.05, 48.15), 0.15, n1v8)

    # SWIRE: J4.14 to R31 on B.Cu
    manhattan(b, pad_xy(j4, "14"), pad_xy(r31, "1"), 0.12, n_sw, pcbnew.B_Cu, first="x")
    # F stubs
    jx, jy = pad_xy(j4, "14")
    add_via(b, jx, jy, n_sw)
    rx, ry = pad_xy(r31, "1")
    add_via(b, rx, ry, n_sw)

    for fp, pn in [(c29, "2"), (c42, "2"), (c43, "2"), (c44, "2"), (c45, "2"), (u8, "2")]:
        x, y = pad_xy(fp, pn)
        add_track(b, (x, y), (x, y + 0.7), 0.15, n_gnd)
        add_via(b, x, y + 0.7, n_gnd)


def route_mipi_gpio(b):
    u2 = b.FindFootprintByReference("U2")
    j4 = b.FindFootprintByReference("J4")
    u8 = b.FindFootprintByReference("U8")
    u10 = b.FindFootprintByReference("U10")
    r31 = b.FindFootprintByReference("R31")

    # MIPI: mostly F.Cu in cleared corridor strip (matched elbows, 0.5 mm pair gap)
    for upad, jpad, netname, w, bus_x in [
        ("81", "35", "DSI_D0P", 0.09, 27.0),
        ("80", "36", "DSI_D0N", 0.09, 27.5),
        ("85", "39", "DSI_CKP", 0.09, 28.5),
        ("84", "40", "DSI_CKN", 0.09, 29.0),
    ]:
        net = ensure(b, netname)
        ux, uy = pad_xy(u2, upad)
        jx, jy = pad_xy(j4, jpad)
        gather_y = 42.0
        add_track(b, (ux, uy), (ux, gather_y), w, net)
        add_track(b, (ux, gather_y), (bus_x, gather_y), w, net)
        add_track(b, (bus_x, gather_y), (bus_x, jy + 1.0), w, net)
        add_track(b, (bus_x, jy + 1.0), (jx, jy + 1.0), w, net)
        add_track(b, (jx, jy + 1.0), (jx, jy), w, net)

    # LCD_RST / TE on B.Cu west channel
    for upad, jpad, netname, bus_x in [
        ("2", "16", "LCD_RST", 23.0),
        ("3", "15", "LCD_TE", 23.6),
    ]:
        net = ensure(b, netname)
        ux, uy = pad_xy(u2, upad)
        jx, jy = pad_xy(j4, jpad)
        u_via = (22.8, uy)
        j_via = (jx, jy + 0.9)
        add_track(b, (ux, uy), u_via, 0.12, net)
        add_via(b, *u_via, net)
        add_track(b, (jx, jy), j_via, 0.12, net)
        add_via(b, *j_via, net)
        manhattan(b, u_via, (bus_x, u_via[1]), 0.12, net, pcbnew.B_Cu, first="x")
        add_track(b, (bus_x, u_via[1]), (bus_x, j_via[1]), 0.12, net, pcbnew.B_Cu)
        manhattan(b, (bus_x, j_via[1]), j_via, 0.12, net, pcbnew.B_Cu, first="x")

    # LCD_EN short F.Cu multi-drop in cleared west riser + y=44 channel
    n_en = ensure(b, "LCD_EN")
    ux, uy = pad_xy(u2, "4")
    riser = (23.2, uy)
    add_track(b, (ux, uy), riser, 0.12, n_en)
    junc = (23.2, 44.0)
    add_track(b, riser, junc, 0.12, n_en)

    u8x, u8y = pad_xy(u8, "3")
    t10x, t10y = pad_xy(u10, "7")
    r2x, r2y = pad_xy(r31, "2")

    # U8
    manhattan(b, junc, (u8x, u8y), 0.12, n_en, first="x")
    # U10 along cleared y=44 channel
    manhattan(b, junc, (t10x, 44.0), 0.12, n_en, first="x")
    add_track(b, (t10x, 44.0), (t10x, t10y), 0.12, n_en)
    # R31
    manhattan(b, junc, (r2x, r2y), 0.12, n_en, first="x")


def stitch_j4_gnd(b):
    j4 = b.FindFootprintByReference("J4")
    n_gnd = ensure(b, "GND")
    gnd_pads = []
    for p in j4.Pads():
        if p.GetNetname() == "GND":
            gnd_pads.append((p.GetNumber(), fmm(p.GetPosition().x), fmm(p.GetPosition().y)))
    # Sort by x and daisy-chain neighbors + via every ~3 pads
    gnd_pads.sort(key=lambda t: t[1])
    for i in range(len(gnd_pads) - 1):
        a = gnd_pads[i]
        c = gnd_pads[i + 1]
        # only link if close
        if abs(a[1] - c[1]) < 1.2 and abs(a[2] - c[2]) < 3.5:
            manhattan(b, (a[1], a[2]), (c[1], c[2]), 0.15, n_gnd, first="y")
    # vias on a few pads into GND plane
    for num, x, y in gnd_pads[::3]:
        vy = y + 0.85 if abs(y - gnd_pads[0][2]) < 0.2 else y - 0.85
        add_track(b, (x, y), (x, vy), 0.15, n_gnd)
        add_via(b, x, vy, n_gnd)


def write_doc(before, after, drc_summary: str):
    def row(ref):
        b_ = before["placements"].get(ref)
        a = after["placements"].get(ref)
        if not b_ or not a:
            return f"| {ref} | — | — |"
        return (
            f"| {ref} | ({b_[0]:.2f}, {b_[1]:.2f}) r{b_[2]} "
            f"| ({a[0]:.2f}, {a[1]:.2f}) r{a[2]} |"
        )

    def net_row(net):
        bl = before["lengths"].get(net, 0.0)
        al = after["lengths"].get(net, 0.0)
        bv = before["vias"].get(net, 0)
        av = after["vias"].get(net, 0)
        ly = ", ".join(after["layers"].get(net, []))
        return f"| `{net}` | {bl:.3f} / {bv} | {al:.3f} / {av} | {ly} |"

    refs = [
        "J4", "U10", "L5", "L6", "U8", "C29",
        "C42", "C43", "C44", "C45", "R29", "R31",
        "C46", "C47", "C48", "C49", "C50", "C51", "U2",
    ]
    nets = [
        "LCD_EN", "LCD_RST", "LCD_TE", "LCD_SWIRE",
        "DSI_D0P", "DSI_D0N", "DSI_CKP", "DSI_CKN",
        "LCD_3V3", "LCD_1V8", "ELVDD", "ELVSS", "EL_SWP", "EL_SWN", "EL_CT",
    ]
    body = f"""# Display layout relax study

Branch intent: `feat/display-layout-relax` (from `feat/display-2p4-aod-rm690b0` @ `53666561e8`).
Date: 2026-09-06 (Asia/Shanghai). KiCad on box: 9.0.2. **Not fab-ready.**

## Why

Prior tip electrically closed display nets but packed routes through the SoC pocket
despite ~58×110 mm free board area (`LCD_EN` ~187 mm / 22 vias; heavy F.Cu under U2).
User allows component moves for a cleaner corridor study.

## What changed

- Kept **J4** near the original north-of-SoC site (mild shift to y=37) so it does not land on KEY_UP copper.
- Moved **U8 + C29 + C42–C45 + R29/R31** to the **west flank** (x≈14–23, y≈44–48), clearing the SoC↔FPC strip.
- Moved **U10 + L5/L6 + EL caps** to the **east flank** (x≈41–53, y≈39–48) as a tight SW-loop cluster.
- Deleted prior display copper; re-routed MIPI 1-lane mostly on **B.Cu** with short F.Cu stubs;
  `LCD_RST`/`LCD_TE`/`LCD_EN` on a west B.Cu channel; EL/VCI as local islands.
- `fabrication_released` left **false**.

## Placement before → after (mm)

| Ref | Before | After |
|---|---|---|
{chr(10).join(row(r) for r in refs)}

## Net length / via count (before → after)

| Net | before mm / vias | after mm / vias | after layers |
|---|---:|---:|---|
{chr(10).join(net_row(n) for n in nets)}

### LCD_EN path note

- Copper-sum length (all branches U2/U8/U10/R31): see table.
- U2→U10 Manhattan after place: **{after.get("lcd_en_u2_u10_manhattan", "?")} mm** (before place distance was ~{before.get("lcd_en_u2_u10_manhattan", "?")} mm).

## Under-U2 F.Cu track midpoints (pad bbox +0.5 mm)

| | All nets | Display nets only |
|---|---:|---:|
| Before | {before["fcu_under_u2"]} | {before.get("fcu_under_u2_display", "?")} |
| After | {after["fcu_under_u2"]} | {after.get("fcu_under_u2_display", "?")} |

## Connectivity / DRC

- pcbnew unconnected after zone fill: **{after["unconnected"]}** (baseline: {before["unconnected"]})
- Track/via totals after: {after["tracks"]} tracks, {after["via_count"]} vias
- kicad-cli DRC summary:

```
{drc_summary.strip() or "(not run or empty)"}
```

## Remaining issues (honest)

- Study routing: no impedance / length-match signoff; via-near-pad used for speed.
- J4 GND pads stitched + vias — may still need pour cleanup.
- Non-display F.Cu under U2 (CORE/3V3/SD/…) not redesigned.
- Possible residual shorts where new B.Cu crosses pre-existing digital (check DRC).
- Molex 502598 land and TPS65631 paste remain unsigned.
- Do **not** treat as fab-ready.

## Helper

`tools/relax_display_layout.py` — restores `verification/*.pre_layout_relax.bak`, then places/routes.
"""
    DOC.write_text(body)
    return DOC


def main():
    os.chdir(PROJ)
    if BAK.exists():
        shutil.copy2(BAK, PCB)
        print("restored from", BAK)

    b = pcbnew.LoadBoard(str(PCB))
    before = metrics(b, "before", do_fill=True)
    print("BEFORE LCD_EN", before["lengths"].get("LCD_EN"), "vias", before["vias"].get("LCD_EN"))
    print("BEFORE F.Cu under U2", before["fcu_under_u2"], "display", before["fcu_under_u2_display"])
    print("BEFORE unconn", before["unconnected"], "U2-U10 manh", before["lcd_en_u2_u10_manhattan"])

    if BAK.exists():
        shutil.copy2(BAK, PCB)
    b = pcbnew.LoadBoard(str(PCB))

    n = delete_copper(b)
    print("deleted copper items", n)
    place_island(b)
    collateral, nch = clear_channels(b)
    print("cleared channel items", nch, "collateral nets", sorted(collateral.items(), key=lambda kv: -kv[1])[:12])
    clear_box_nets(b, (12.0, 42.0, 24.0, 49.0), {"1V8"})
    route_el_island(b)
    route_vci_vddio(b)
    route_mipi_gpio(b)
    stitch_j4_gnd(b)

    after = metrics(b, "after", do_fill=True)
    print("AFTER LCD_EN", after["lengths"].get("LCD_EN"), "vias", after["vias"].get("LCD_EN"))
    print("AFTER F.Cu under U2", after["fcu_under_u2"], "display", after["fcu_under_u2_display"])
    print("unconnected", after["unconnected"], "U2-U10 manh", after["lcd_en_u2_u10_manhattan"])
    for ref, xyz in sorted(after["placements"].items()):
        print(f"  {ref}: {xyz}")

    pcbnew.SaveBoard(str(PCB), b)
    after["collateral_channel_nets"] = collateral
    METRICS.write_text(json.dumps({"before": before, "after": after}, indent=2))
    write_doc(before, after, drc_summary="(pending kicad-cli)")
    print("saved", PCB)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
