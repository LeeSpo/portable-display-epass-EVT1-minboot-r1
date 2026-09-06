#!/usr/bin/env python3
"""KD024 display island placement + local EL fanout (KiCad 9)."""
from __future__ import annotations
import os
from pathlib import Path
import pcbnew

PROJ = Path(__file__).resolve().parents[1]
PCB = PROJ / "portable_display_epass.kicad_pcb"
PRETTY = str(PROJ / "sameat.pretty")
COPPER = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

def mm(x): return int(round(x * 1_000_000))
def fmm(v): return v / 1_000_000.0

def ensure(b, n):
    net = b.FindNet(n)
    if net is None or net.GetNetCode() == 0:
        net = pcbnew.NETINFO_ITEM(b, n)
        b.Add(net)
    return net

def setn(fp, num, net):
    for p in fp.Pads():
        if p.GetNumber() == str(num):
            p.SetNet(net)

def mark_dnp(fp):
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_DNP | pcbnew.FP_EXCLUDE_FROM_POS_FILES)

def place(b, lib, ref, val, x, y, rot=0.0, is_dnp=False):
    old = b.FindFootprintByReference(ref)
    if old is not None:
        b.Remove(old)
    fp = pcbnew.FootprintLoad(PRETTY, lib)
    if fp is None:
        raise RuntimeError(lib)
    fp.SetReference(ref)
    fp.SetValue(val)
    fp.SetFPIDAsString(f"Sameat:{lib}")
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
    fp.SetLayer(pcbnew.F_Cu)
    if is_dnp:
        mark_dnp(fp)
    b.Add(fp)
    return fp

def xy(fp, n):
    for p in fp.Pads():
        if p.GetNumber() == str(n):
            return fmm(p.GetPosition().x), fmm(p.GetPosition().y)
    raise KeyError(n)

def add_tr(b, a, c, w, net):
    if a == c:
        return
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
    t.SetWidth(mm(w))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    b.Add(t)

def add_via(b, x, y, net):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetDrill(mm(0.2))
    for lyr in COPPER:
        try:
            v.SetWidth(lyr, mm(0.45))
        except Exception:
            pass
    try:
        v.SetFrontWidth(mm(0.45))
    except Exception:
        pass
    v.SetNet(net)
    b.Add(v)

def clear_box(b, xmin, ymin, xmax, ymax):
    to_delete = []
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_VIA_T:
            pts = [(fmm(t.GetPosition().x), fmm(t.GetPosition().y))]
        else:
            pts = [
                (fmm(t.GetStart().x), fmm(t.GetStart().y)),
                (fmm(t.GetEnd().x), fmm(t.GetEnd().y)),
            ]
        if any(xmin <= x <= xmax and ymin <= y <= ymax for x, y in pts):
            to_delete.append(t)
    for t in to_delete:
        b.Delete(t)
    return len(to_delete)

def main():
    os.chdir(PROJ)
    b = pcbnew.LoadBoard(str(PCB))
    for n in [
        "ELVDD", "ELVSS", "EL_SWP", "EL_SWN", "EL_CT", "LCD_1V8", "LCD_TE", "LCD_TE1",
        "LCD_SWIRE", "LCD_3V3", "LCD_EN", "LCD_RST", "DSI_D0P", "DSI_D0N", "DSI_CKP",
        "DSI_CKN", "VSYS", "GND", "1V8",
    ]:
        ensure(b, n)

    u2 = b.FindFootprintByReference("U2")
    if u2:
        for p in u2.Pads():
            if p.GetNumber() == "3":
                p.SetNet(ensure(b, "LCD_TE"))

    for ref, (x, y, val) in {
        "U7": (52, 5, "TPS61169DCKR"),
        "L4": (52, 9, "10uH/1.5A"),
        "D4": (52, 13, "SS16"),
        "R19": (52, 17, "2.55R 1%"),
        "C27": (52, 21, "1u/25V"),
        "C28": (52, 24, "100n"),
    }.items():
        fp = b.FindFootprintByReference(ref)
        if not fp:
            continue
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetValue(val)
        mark_dnp(fp)
        for p in fp.Pads():
            p.SetNetCode(0)

    j4o = b.FindFootprintByReference("J4")
    if j4o is not None:
        b.Remove(j4o)

    n1 = clear_box(b, 22.0, 36.2, 46.5, 39.8)
    n2 = clear_box(b, 40.0, 27.0, 54.0, 37.5)
    print("cleared", n1, n2)

    j4 = place(b, "FPC45", "J4", "KD024EGOIN152-01", 34.0, 38.0)
    for k, v in {
        "1": "GND", "2": "GND", "3": "ELVSS", "4": "ELVSS", "5": "GND", "6": "ELVDD",
        "7": "ELVDD", "8": "GND", "9": "LCD_3V3", "10": "GND", "11": "LCD_1V8", "12": "GND",
        "13": "LCD_TE1", "14": "LCD_SWIRE", "15": "LCD_TE", "16": "LCD_RST", "17": "GND",
        "30": "GND", "31": "GND", "32": "GND", "33": "GND", "34": "GND", "35": "DSI_D0P",
        "36": "DSI_D0N", "37": "GND", "38": "GND", "39": "DSI_CKP", "40": "DSI_CKN",
        "41": "GND", "42": "GND", "43": "GND", "44": "GND", "45": "GND",
    }.items():
        setn(j4, k, ensure(b, v))
    for n in range(18, 30):
        for p in j4.Pads():
            if p.GetNumber() == str(n):
                p.SetNetCode(0)

    u10 = place(b, "WSON-12", "U10", "TPS65631DPDR", 46.0, 32.5)
    for k, v in {
        "1": "EL_SWP", "2": "GND", "3": "ELVDD", "4": "ELVDD", "5": "GND", "6": "GND",
        "7": "LCD_EN", "8": "EL_CT", "9": "ELVSS", "10": "EL_SWN", "11": "VSYS",
        "12": "VSYS", "13": "GND",
    }.items():
        setn(u10, k, ensure(b, v))

    l5 = place(b, "IND_2x2", "L5", "4.7uH", 41.0, 29.0)
    setn(l5, "1", ensure(b, "VSYS")); setn(l5, "2", ensure(b, "EL_SWP"))
    l6 = place(b, "IND_2x2", "L6", "4.7uH", 51.0, 29.0)
    setn(l6, "1", ensure(b, "EL_SWN")); setn(l6, "2", ensure(b, "GND"))
    c46 = place(b, "0603", "C46", "10u", 47.5, 26.5, 90)
    setn(c46, "1", ensure(b, "VSYS")); setn(c46, "2", ensure(b, "GND"))
    c47 = place(b, "0603", "C47", "10u", 50.5, 26.5, 90)
    setn(c47, "1", ensure(b, "VSYS")); setn(c47, "2", ensure(b, "GND"))
    c48 = place(b, "0603", "C48", "10u", 41.0, 35.0, 90)
    setn(c48, "1", ensure(b, "ELVDD")); setn(c48, "2", ensure(b, "GND"))
    c49 = place(b, "0603", "C49", "10u", 50.0, 35.0, 90)
    setn(c49, "1", ensure(b, "ELVSS")); setn(c49, "2", ensure(b, "GND"))
    c50 = place(b, "0603", "C50", "10u", 53.0, 33.0, 90)
    setn(c50, "1", ensure(b, "ELVSS")); setn(c50, "2", ensure(b, "GND"))
    c51 = place(b, "0402", "C51", "100n", 48.0, 36.5)
    setn(c51, "1", ensure(b, "EL_CT")); setn(c51, "2", ensure(b, "GND"))

    c42 = place(b, "0603", "C42", "1u", 38.0, 41.5, 90)
    setn(c42, "1", ensure(b, "LCD_3V3")); setn(c42, "2", ensure(b, "GND"))
    c43 = place(b, "0402", "C43", "100n", 40.0, 41.5, 90)
    setn(c43, "1", ensure(b, "LCD_3V3")); setn(c43, "2", ensure(b, "GND"))
    r29 = place(b, "0402", "R29", "0R", 42.0, 41.5)
    setn(r29, "1", ensure(b, "1V8")); setn(r29, "2", ensure(b, "LCD_1V8"))
    c44 = place(b, "0603", "C44", "1u", 38.0, 44.0, 90)
    setn(c44, "1", ensure(b, "LCD_1V8")); setn(c44, "2", ensure(b, "GND"))
    c45 = place(b, "0402", "C45", "100n", 40.0, 44.0, 90)
    setn(c45, "1", ensure(b, "LCD_1V8")); setn(c45, "2", ensure(b, "GND"))
    r31 = place(b, "0402", "R31", "0R", 42.0, 44.0, is_dnp=True)
    setn(r31, "1", ensure(b, "LCD_SWIRE")); setn(r31, "2", ensure(b, "LCD_EN"))

    # Local EL island
    add_tr(b, xy(l5, "2"), xy(u10, "1"), 0.25, ensure(b, "EL_SWP"))
    add_tr(b, xy(l5, "1"), xy(c46, "1"), 0.25, ensure(b, "VSYS"))
    add_tr(b, xy(c46, "1"), xy(c47, "1"), 0.25, ensure(b, "VSYS"))
    a, c = xy(c47, "1"), xy(u10, "12")
    add_tr(b, a, (c[0], a[1]), 0.25, ensure(b, "VSYS"))
    add_tr(b, (c[0], a[1]), c, 0.25, ensure(b, "VSYS"))
    add_tr(b, xy(u10, "12"), xy(u10, "11"), 0.25, ensure(b, "VSYS"))
    add_tr(b, xy(u10, "10"), xy(l6, "1"), 0.25, ensure(b, "EL_SWN"))
    add_tr(b, xy(u10, "3"), xy(u10, "4"), 0.25, ensure(b, "ELVDD"))
    add_tr(b, xy(u10, "3"), xy(c48, "1"), 0.25, ensure(b, "ELVDD"))
    add_tr(b, xy(u10, "9"), xy(c49, "1"), 0.25, ensure(b, "ELVSS"))
    add_tr(b, xy(c49, "1"), xy(c50, "1"), 0.25, ensure(b, "ELVSS"))
    add_tr(b, xy(u10, "8"), xy(c51, "1"), 0.15, ensure(b, "EL_CT"))
    add_via(b, *xy(u10, "13"), ensure(b, "GND"))
    for fp, pn, dx, dy in [
        (l6, "2", 1.2, 0), (c46, "2", 0, 1.0), (c47, "2", 0, 1.0),
        (c48, "2", -1.0, 0), (c49, "2", 0, 1.0), (c50, "2", 1.0, 0), (c51, "2", 0, 1.0),
    ]:
        x, y = xy(fp, pn)
        add_tr(b, (x, y), (x + dx, y + dy), 0.2, ensure(b, "GND"))
        add_via(b, x + dx, y + dy, ensure(b, "GND"))
    for pn in ["2", "5", "6"]:
        x, y = xy(u10, pn)
        add_tr(b, (x, y), (x - 1.2, y), 0.25, ensure(b, "GND"))
        add_via(b, x - 1.2, y, ensure(b, "GND"))
    vx, vy = xy(c46, "1")
    add_tr(b, (vx, vy), (vx, vy - 1.0), 0.25, ensure(b, "VSYS"))
    add_via(b, vx, vy - 1.0, ensure(b, "VSYS"))
    x, y = xy(u10, "7")
    add_tr(b, (x, y), (x, y + 1.2), 0.15, ensure(b, "LCD_EN"))

    add_tr(b, xy(c42, "1"), xy(c43, "1"), 0.15, ensure(b, "LCD_3V3"))
    add_tr(b, xy(c44, "1"), xy(c45, "1"), 0.15, ensure(b, "LCD_1V8"))
    add_tr(b, xy(r29, "2"), xy(c45, "1"), 0.15, ensure(b, "LCD_1V8"))
    for fp, pn in [(c42, "2"), (c43, "2"), (c44, "2"), (c45, "2")]:
        x, y = xy(fp, pn)
        add_tr(b, (x, y), (x, y + 1.0), 0.15, ensure(b, "GND"))
        add_via(b, x, y + 1.0, ensure(b, "GND"))
    rx, ry = xy(r29, "1")
    add_tr(b, (rx, ry), (rx + 1.0, ry), 0.15, ensure(b, "1V8"))
    add_via(b, rx + 1.0, ry, ensure(b, "1V8"))
    add_tr(b, xy(r31, "1"), xy(j4, "14"), 0.15, ensure(b, "LCD_SWIRE"))

    for p, n in [
        ("35", "DSI_D0P"), ("36", "DSI_D0N"), ("39", "DSI_CKP"), ("40", "DSI_CKN"),
        ("15", "LCD_TE"), ("16", "LCD_RST"), ("9", "LCD_3V3"), ("11", "LCD_1V8"),
        ("6", "ELVDD"), ("3", "ELVSS"),
    ]:
        x, y = xy(j4, p)
        add_tr(b, (x, y), (x, y + 0.7), 0.12, ensure(b, n))

    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    b.BuildConnectivity()
    print("unconnected", b.GetConnectivity().GetUnconnectedCount(True))
    pcbnew.SaveBoard(str(PCB), b)
    for ref in ["J4", "U10", "L5", "L6", "C46", "C48", "C42", "R29", "R31", "U7", "U8"]:
        fp = b.FindFootprintByReference(ref)
        print(
            f"{ref}: ({fmm(fp.GetPosition().x):.2f},{fmm(fp.GetPosition().y):.2f}) "
            f"{fp.GetFPIDAsString()} dnp={bool(fp.GetAttributes() & pcbnew.FP_DNP)}"
        )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
