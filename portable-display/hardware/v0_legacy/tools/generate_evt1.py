#!/usr/bin/env python3
"""Generate the self-contained KiCad EVT1 design and manufacturing metadata.

The design is intentionally data driven: symbol pin numbers, PCB pad numbers and
the BOM are emitted from the same Device records so that the three views cannot
silently drift apart.  KiCad itself remains the authority for ERC/DRC and plots.
"""

from __future__ import annotations

import csv
import heapq
import json
import math
import os
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "verification" / "design_metadata"
LIB = ROOT / "sameat.pretty"
NS = uuid.UUID("2b818650-a5d9-4e5d-af21-2d46ab184ac6")
DISPLAY_NETS = {
    "DSI_D0N", "DSI_D0P", "DSI_D1N", "DSI_D1P", "DSI_CKN", "DSI_CKP",
    "LCD_RST", "LCD_TE", "LCD_EN", "LCD_3V3", "LCD_1V8",
    "ELVDD", "ELVSS", "LCD_SWIRE", "LCD_TE1",
    # Legacy TFT backlight nets kept only while U7 chain is DNP:
    "LEDA", "LEDK", "BL_SW", "LCD_PWM",
}
PLANE_NETS = {"GND", "3V3", "CORE_0V93", "1V8", "DRAM_1V5", "RTC_3V3", "VSYS", "VBAT", "VBUS", "SD_3V3"}
VIA_SIZE = 0.40
VIA_DRILL = 0.20
HD_WIDTH = 0.09
HD_CLEAR = 0.09
NORM_WIDTH = 0.15
USB_WIDTH = 0.15
USB_GAP = 0.15
V851_RINGS = (1.15, 1.90, 2.65)


def uid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


def q(value: object) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


@dataclass
class Pad:
    number: str
    x: float
    y: float
    sx: float
    sy: float
    shape: str = "roundrect"
    angle: float = 0.0
    kind: str = "smd"
    layers: tuple[str, ...] = ("F.Cu", "F.Paste", "F.Mask")
    drill: float | None = None


@dataclass
class Device:
    ref: str
    value: str
    footprint: str
    sheet: str
    x: float
    y: float
    pins: dict[str, tuple[str, str | None]]
    mpn: str = ""
    lcsc: str = ""
    datasheet: str = ""
    rotation: float = 0.0
    dnp: bool = False
    note: str = ""
    pads: list[Pad] = field(default_factory=list)


def two_pad(pitch: float = 1.0, size: tuple[float, float] = (0.6, 0.7)) -> list[Pad]:
    return [
        Pad("1", -pitch / 2, 0, *size),
        Pad("2", pitch / 2, 0, *size),
    ]


def row_pads(count: int, pitch: float, sy: float = 1.2) -> list[Pad]:
    start = -(count - 1) * pitch / 2
    return [Pad(str(i + 1), start + i * pitch, 0, min(0.32, pitch * 0.62), sy, "rect") for i in range(count)]


def dual_pads(count: int, body_x: float, pitch: float, pad_size=(1.0, 0.32)) -> list[Pad]:
    assert count % 2 == 0
    side = count // 2
    ys = [-(side - 1) * pitch / 2 + i * pitch for i in range(side)]
    pads: list[Pad] = []
    for i, yy in enumerate(ys):
        pads.append(Pad(str(i + 1), -body_x / 2, yy, *pad_size))
    for i, yy in enumerate(reversed(ys)):
        pads.append(Pad(str(side + i + 1), body_x / 2, yy, *pad_size))
    return pads


def qfn_pads(count: int, body: float, pitch: float, ep_number: str, ep: float) -> list[Pad]:
    assert count % 4 == 0
    side = count // 4
    span = (side - 1) * pitch
    edge = body / 2 + 0.25
    pads: list[Pad] = []
    for i in range(side):
        pads.append(Pad(str(i + 1), -edge, -span / 2 + i * pitch, 0.70, 0.18))
    for i in range(side):
        pads.append(Pad(str(side + i + 1), -span / 2 + i * pitch, edge, 0.18, 0.70))
    for i in range(side):
        pads.append(Pad(str(2 * side + i + 1), edge, span / 2 - i * pitch, 0.70, 0.18))
    for i in range(side):
        pads.append(Pad(str(3 * side + i + 1), span / 2 - i * pitch, -edge, 0.18, 0.70))
    pads.append(Pad(ep_number, 0, 0, ep, ep, "rect"))
    return pads


def lga12_pads() -> list[Pad]:
    # LIS2DW12 DS11811 Rev9 pp.4,56: TOP view, 4-2-4-2 arrangement.
    # TN0018: 0.275x0.25 package terminal + 0.1mm in each dimension.
    coords = [(-.7625,-.75),(-.7625,-.25),(-.7625,.25),(-.7625,.75),
              (-.25,.7625),(.25,.7625),(.7625,.75),(.7625,.25),
              (.7625,-.25),(.7625,-.75),(.25,-.7625),(-.25,-.7625)]
    return [Pad(str(i),x,y,*((.35,.375) if i in [5,6,11,12] else (.375,.35)))
            for i,(x,y) in enumerate(coords,1)]


def usb4105_pads() -> list[Pad]:
    loc = {
        "A1": (-3.2, -3.68, .6), "A4": (-2.4, -3.68, .6), "A5": (-1.25, -3.68, .3),
        "A6": (-.25, -3.68, .3), "A7": (.25, -3.68, .3), "A8": (1.25, -3.68, .3),
        "A9": (2.4, -3.68, .6), "A12": (3.2, -3.68, .6),
        "B1": (3.2, -3.68, .6), "B4": (2.4, -3.68, .6), "B5": (1.75, -3.68, .3),
        "B6": (.75, -3.68, .3), "B7": (-.75, -3.68, .3), "B8": (-1.75, -3.68, .3),
        "B9": (-2.4, -3.68, .6), "B12": (-3.2, -3.68, .6),
    }
    pads = [Pad(n, x, y, sx, 1.15) for n, (x, y, sx) in loc.items()]
    for i, (x, y, sy) in enumerate([(-4.32, -3.105, 2.1), (-4.32, 1.075, 1.8), (4.32, -3.105, 2.1), (4.32, 1.075, 1.8)], 1):
        pads.append(Pad(f"SH{i}", x, y, 1.0, sy, "oval", kind="thru_hole", layers=("*.Cu", "*.Mask"), drill=.6))
    return pads


def microsd_pads() -> list[Pad]:
    # MUP-M617-2 contact row; shell/CD geometry follows the vendor-recommended land pattern.
    pads = [Pad(str(i + 1), -3.5 + i, -4.35, .55, 1.4, "rect") for i in range(8)]
    pads += [Pad("9", 5.1, -1.8, .7, 1.2), Pad("10", -6.0, 1.8, 1.3, 1.8), Pad("11", 6.0, 1.8, 1.3, 1.8)]
    pads += [Pad("12", -5.6, -3.8, 1.2, 1.5), Pad("13", 5.6, -3.8, 1.2, 1.5)]
    return pads


def side_switch_pads() -> list[Pad]:
    return [Pad("1", -2.2, -1.25, 1.1, 1.1), Pad("2", -2.2, 1.25, 1.1, 1.1), Pad("3", 2.2, 0, 1.2, 1.4)]


def crystal4_pads() -> list[Pad]:
    return [Pad("1", -1.2, -.9, 1.0, .9), Pad("2", 1.2, -.9, 1.0, .9), Pad("3", 1.2, .9, 1.0, .9), Pad("4", -1.2, .9, 1.0, .9)]


def battery3_pads() -> list[Pad]:
    return [Pad(str(i + 1), -2 + 2 * i, 0, 1.2, 2.2) for i in range(3)]


def test_header_pads(count: int) -> list[Pad]:
    start = -(count - 1) * 1.27 / 2
    return [Pad(str(i + 1), start + i * 1.27, 0, 1.0, 1.0, "circle", kind="thru_hole", layers=("*.Cu", "*.Mask"), drill=.55) for i in range(count)]


def v851_pins() -> dict[str, tuple[str, str | None]]:
    names = {
        1:"PD18",2:"PD19",3:"PD20",4:"PD21",5:"VCC33_PF_PD",6:"PF0_SDC0_D1",7:"PF1_SDC0_D0",
        8:"PF2_SDC0_CLK",9:"PF3_SDC0_CMD",10:"PF4_SDC0_D3",11:"PF5_SDC0_D2",12:"PF6_DBG_CLK",
        13:"VDD_SYS0",14:"VCC_LDOA_PLL",15:"DXOUT",16:"DXIN",17:"VDD_SYS1",18:"PE13",19:"PE12",
        20:"PE11",21:"PE4",22:"VCC_PE",23:"PE2",24:"PE7",25:"PE0",26:"PE5",27:"PE8",28:"PE9",
        29:"PE3",30:"PE6",31:"PE1",32:"PE10",33:"VDD_SYS2",34:"VCC_DRAM0",35:"VDD_SYS3",
        36:"VCC_DRAM1",37:"VDD18_DRAM",38:"PH14",39:"PH13",40:"PH12",41:"PH11",42:"PH10",
        43:"PH9",44:"VCC_IO",45:"PH0",46:"GPADC0",47:"VDD33",48:"AVCC",49:"LINEOUTP",50:"VRA1",
        51:"AGND",52:"MICIN1N",53:"MICIN1P",54:"VDD_SYS4",55:"VCC_PC",56:"PC1_SPI0_CS",57:"PC0_SPI0_CLK",
        58:"PC3_SPI0_MISO_BOOT1",59:"PC2_SPI0_MOSI_BOOT0",60:"PC5_SPI0_HOLD",61:"PC4_SPI0_WP",
        62:"VCC_PA_MCSI",63:"PA11",64:"PA10",65:"PA9",66:"PA8",67:"PA7",68:"PA6",69:"PA5",70:"PA4",
        71:"PA3",72:"PA2",73:"PA1",74:"PA0",75:"VDD_SYS5",76:"USB0_DP",77:"USB0_DM",78:"VCC33_USB",
        79:"VCC18_MDSI",80:"PD1_DSI_D0N",81:"PD2_DSI_D0P",82:"PD3_DSI_D1N",83:"PD4_DSI_D1P",
        84:"PD5_DSI_CKN",85:"PD6_DSI_CKP",86:"PD7",87:"PD8",88:"VDD_SYS6",89:"EPAD",
    }
    net: dict[int, str] = {
        2:"LCD_RST",3:"LCD_TE",4:"LCD_EN",5:"3V3",6:"SD_D1",7:"SD_D0",8:"SD_CLK",9:"SD_CMD",
        10:"SD_D3",11:"SD_D2",12:"SD_DET",13:"CORE_0V93",14:"SOC_LDO_1V8",15:"XOUT",16:"XIN",
        17:"CORE_0V93",21:"I2C0_SCL",22:"3V3",23:"PMIC_IRQ_N",24:"RTC_INT_N",25:"E907_TX",
        26:"I2C0_SDA",30:"ACCEL_INT_N",31:"E907_RX",33:"CORE_0V93",34:"DRAM_1V5",35:"CORE_0V93",
        36:"DRAM_1V5",37:"SOC_LDO_1V8",38:"PMIC_SDA",39:"PMIC_SCL",40:"SD_PWR_EN",41:"STATUS_LED",
        42:"UART0_RX",43:"UART0_TX",44:"3V3",45:"WAKE_PULSE_N",46:"ADC_KEYS",47:"3V3",48:"SOC_AVCC",
        50:"VRA1",51:"GND",54:"CORE_0V93",55:"3V3",58:"BOOT1",
        59:"BOOT0",62:"SOC_LDO_1V8",75:"CORE_0V93",76:"USB_DP",
        77:"USB_DM",78:"3V3",79:"SOC_LDO_1V8",80:"DSI_D0N",81:"DSI_D0P",
        84:"DSI_CKN",85:"DSI_CKP",88:"CORE_0V93",89:"GND",
    }
    return {str(i):(names[i], net.get(i)) for i in range(1, 90)}


def axp_pins() -> dict[str, tuple[str, str | None]]:
    names = {
        1:"CHGLED",2:"VREF",3:"GND",4:"FB3",5:"LX3",6:"VIN3",7:"VIN4",8:"LX4",9:"FB4",
        10:"CPUSLDO",11:"DLDO2_DC4SW",12:"BLDO1",13:"BLDOIN",14:"BLDO2",15:"ALDO4",16:"ALDO3",
        17:"ALDOIN",18:"ALDO1",19:"ALDO2",20:"DLDO1_DC1SW",21:"FB1",22:"LX1",23:"VIN1",24:"VIN2",
        25:"LX2",26:"FB2",27:"VBACKUP",28:"VRTC",29:"PWROK",30:"PWRON",31:"TS",32:"GPIO1_FB5_RTCLDO2",
        33:"BAT",34:"VSYS",35:"SW",36:"VMID",37:"VBUS",38:"IRQ",39:"SDA",40:"SCK",41:"EPAD",
    }
    net = {
        1:"CHGLED_N",2:"VREF",3:"GND",4:"CORE_0V93",5:"LX_CORE",6:"VSYS",7:"VSYS",8:"LX_DRAM",
        9:"DRAM_1V5",13:"3V3",17:"3V3",18:"1V8",21:"3V3",22:"LX_3V3",23:"VSYS",24:"VSYS",
        27:"PMIC_BACKUP",28:"RTC_3V3",30:"PWRON_N",31:"BAT_NTC",33:"VBAT",34:"VSYS",
        36:"VSYS",37:"VBUS",38:"PMIC_IRQ_N",39:"PMIC_SDA",40:"PMIC_SCL",41:"GND",
    }
    return {str(i):(names[i], net.get(i)) for i in range(1, 42)}


def add(devs: list[Device], ref: str, value: str, fp: str, sheet: str, x: float, y: float,
        pins: dict[str, tuple[str, str | None]], **kw) -> Device:
    d = Device(ref, value, fp, sheet, x, y, pins, **kw)
    if not d.pads:
        if fp == "0402": d.pads = two_pad()
        elif fp == "0603": d.pads = two_pad(1.6, (.8, .95))
        elif fp == "IND_2x2": d.pads = two_pad(2.1, (1.2, 1.8))
        elif fp == "SOT23-3": d.pads = [Pad("1", -.95, -.95, .7, .9), Pad("2", .95, -.95, .7, .9), Pad("3", 0, .95, .7, .9)]
        elif fp == "SOT23-5": d.pads = [Pad("1",-1.2,-.95,.8,.65),Pad("2",-1.2,0,.8,.65),Pad("3",-1.2,.95,.8,.65),Pad("4",1.2,.95,.8,.65),Pad("5",1.2,-.95,.8,.65)]
        elif fp == "SC70-5": d.pads = [Pad("1",-1,-.65,.7,.35),Pad("2",-1,0,.7,.35),Pad("3",-1,.65,.7,.35),Pad("4",1,.65,.7,.35),Pad("5",1,-.65,.7,.35)]
        elif fp == "SOT23-6": d.pads = dual_pads(6, 2.4, .95, (.8,.65))
        elif fp == "SSOP-8": d.pads = dual_pads(8, 3.6, .65, (1.05,.35))
        elif fp == "WSON-8": d.pads = dual_pads(8, 6.4, 1.27, (1.4,.6))
        elif fp == "WSON-12":
            d.pads = dual_pads(12, 2.9, 0.45, (0.70, 0.25)) + [Pad("13", 0, 0, 1.21, 2.02, "rect")]
        elif fp == "LGA-12": d.pads = lga12_pads()
        elif fp == "RTC-8":
            # RV-3028-C7 datasheet v1.3 pp.1-2: PCB top view, pin 1 lower left.
            d.pads = [Pad(str(i+1), -1.35+.9*i, .6, .5, .8, "rect") for i in range(4)]
            d.pads += [Pad(str(8-i), -1.35+.9*i, -.6, .5, .8, "rect") for i in range(4)]
        elif fp == "QFN40": d.pads = qfn_pads(40, 5.0, .4, "41", 3.1)
        elif fp == "QFN88": d.pads = qfn_pads(88, 9.0, .35, "89", 5.2)
        elif fp == "FPC20": d.pads = row_pads(20, .5, 1.2)
        elif fp == "FPC45":
            # Molex SD-502598-003: alternating tails; odd pins at insertion side.
            d.pads = [Pad(str(i), (i-23)*.3, 0 if i%2 else -3.065,
                          .3, .67 if i%2 else .5, "rect") for i in range(1,46)]
            d.pads += [Pad("MP1", -7.4, -.365, .35, 1., "rect"),
                       Pad("MP2", 7.4, -.365, .35, 1., "rect")]
        elif fp == "USB4105": d.pads = usb4105_pads()
        elif fp == "MICROSD": d.pads = microsd_pads()
        elif fp == "SW_SIDE": d.pads = side_switch_pads()
        elif fp == "BAT3": d.pads = battery3_pads()
        elif fp == "HDR8": d.pads = test_header_pads(8)
        elif fp == "XTAL4": d.pads = crystal4_pads()
        elif fp == "D_SOD123": d.pads = two_pad(2.5, (1.2,1.1))
        elif fp == "LED0603": d.pads = two_pad(1.6, (.8,.9))
        else: raise ValueError(f"No footprint generator for {fp}")
    devs.append(d)
    return d


def devices() -> list[Device]:
    d: list[Device] = []
    passive = lambda a, b: {"1":("1",a), "2":("2",b)}

    usb_pins = {
        "A1":("GND", "GND"),"A4":("VBUS","VBUS"),"A5":("CC1","USB_CC1"),"A6":("DP1","USB_DP"),
        "A7":("DM1","USB_DM"),"A8":("SBU1",None),"A9":("VBUS","VBUS"),"A12":("GND","GND"),
        "B1":("GND","GND"),"B4":("VBUS","VBUS"),"B5":("CC2","USB_CC2"),"B6":("DP2","USB_DP"),
        "B7":("DM2","USB_DM"),"B8":("SBU2",None),"B9":("VBUS","VBUS"),"B12":("GND","GND"),
        "SH1":("SHIELD","GND"),"SH2":("SHIELD","GND"),"SH3":("SHIELD","GND"),"SH4":("SHIELD","GND"),
    }
    add(d,"J1","USB4105-GF-A-060","USB4105","power",29,106,usb_pins,mpn="USB4105-GF-A-060",lcsc="C3025063",datasheet="https://gct.co/files/drawings/usb4105.pdf")
    add(d,"R1","5.1k","0402","power",20,101,passive("USB_CC1","GND"),mpn="0402 5.1k 1%",lcsc="C25905")
    add(d,"R2","5.1k","0402","power",22,101,passive("USB_CC2","GND"),mpn="0402 5.1k 1%",lcsc="C25905")
    add(d,"U1","AXP2101","QFN40","power",18,85,axp_pins(),mpn="AXP2101",lcsc="C3036461",datasheet="https://www.x-powers.com/en.php/Info/product_detail/article_id/95")
    add(d,"L1","1uH/2A","IND_2x2","power",9,84,passive("LX_3V3","3V3"),mpn="1uH 2A shielded")
    add(d,"L2","1uH/2A","IND_2x2","power",9,88,passive("LX_CORE","CORE_0V93"),mpn="1uH 2A shielded")
    add(d,"L3","1uH/2A","IND_2x2","power",9,92,passive("LX_DRAM","DRAM_1V5"),mpn="1uH 2A shielded")
    for ref,val,x,y,a,b in [
        ("C1","22u",10,78,"VSYS","GND"),("C2","22u",14,78,"VSYS","GND"),("C3","1u",18,78,"VBAT","GND"),
        ("C4","22u",5,82,"3V3","GND"),("C5","22u",5,85,"3V3","GND"),
        ("C6","22u",5,88,"CORE_0V93","GND"),("C7","22u",5,91,"CORE_0V93","GND"),
        ("C8","22u",5,94,"DRAM_1V5","GND"),("C9","22u",5,97,"DRAM_1V5","GND"),
        ("C10","2.2u",13,93,"1V8","GND"),("C11","1u",13,96,"VREF","GND")]:
        add(d,ref,val,"0603","power",x,y,passive(a,b),mpn=f"0603 {val} X5R")
    add(d,"J2","1S LiPo + NTC","BAT3","power",45,99,{"1":("VBAT","VBAT"),"2":("NTC","BAT_NTC"),"3":("GND","GND")},mpn="S3B-PH-SM4-TB(LF)(SN)",lcsc="C265101")
    add(d,"SW5","POWER","SW_SIDE","power",55,82,{"1":("PWRON","PWRON_N"),"2":("PWRON","PWRON_N"),"3":("GND","GND")},mpn="GT-TC072B-H045-L1",lcsc="C5117859",rotation=90)
    add(d,"R3","4.7k","0402","power",22,78,passive("3V3","PMIC_IRQ_N"),lcsc="C25900")
    add(d,"R4","2.2k","0402","power",24,78,passive("3V3","PMIC_SCL"),lcsc="C25879")
    add(d,"R5","2.2k","0402","power",26,78,passive("3V3","PMIC_SDA"),lcsc="C25879")
    add(d,"D1","CHARGE","LED0603","power",30,82,passive("3V3","CHGLED_A"),mpn="0603 Green LED")
    add(d,"R6","2.2k","0402","power",34,82,passive("CHGLED_A","CHGLED_N"),lcsc="C25879")
    add(d,"U9","USBLC6-2SC6","SOT23-6","power",29,98,{"1":("I/O1","USB_DP"),"2":("GND","GND"),"3":("I/O2","USB_DM"),"4":("I/O2","USB_DM"),"5":("VBUS","VBUS"),"6":("I/O1","USB_DP")},mpn="USBLC6-2SC6",lcsc="C2827654",datasheet="https://www.st.com/resource/en/datasheet/usblc6-2.pdf",rotation=90)
    add(d,"D13","PESD4V0","0402","power",19.5,104,passive("USB_CC1","GND"),mpn="PESD4V0Y1BBSF")
    add(d,"D14","PESD4V0","0402","power",38.5,104,passive("USB_CC2","GND"),mpn="PESD4V0Y1BBSF")
    add(d,"C32","10u","0603","power",15,101,passive("VBUS","GND"),mpn="0603 10u X5R")
    add(d,"C33","1u","0603","power",13,90,passive("RTC_3V3","GND"),mpn="0603 1u X5R")

    # AXP2101 linear-charge variant, datasheet V1.4 Fig. 7-1.
    add(d,"C38","2.2u","0603","power",22,81,passive("VSYS","GND"),note="VMID local bypass; VMID tied to VSYS")
    add(d,"C39","100n","0402","power",18,91,passive("PMIC_BACKUP","GND"),note="No backup cell; do not short backup charger output")
    add(d,"C40","1u","0603","power",13,83,passive("VSYS","GND"),note="VIN3/VIN4 local bypass")
    add(d,"C41","1u","0603","power",23,87,passive("VSYS","GND"),note="VIN1/VIN2 local bypass")

    add(d,"U2","V851s","QFN88","soc",30,56,v851_pins(),mpn="V851s",lcsc="C5365286",datasheet="https://www.allwinnertech.com/index.php?a=index&c=product&id=118")
    add(d,"Y1","24MHz 10ppm","XTAL4","soc",19,56,{"1":("XIN","XIN"),"2":("GND","GND"),"3":("XOUT","XOUT"),"4":("GND","GND")},mpn="24MHz 10ppm 3225")
    add(d,"C12","18p","0402","soc",17,53,passive("XIN","GND"))
    add(d,"C13","18p","0402","soc",17,59,passive("XOUT","GND"))
    # Internal regulators are outputs, not inputs from AXP2101 ALDO1.
    add(d,"C34","2.2u","0603","soc",15.5,61,passive("SOC_LDO_1V8","GND"),note="V851SX internal LDOA output bypass")
    add(d,"C35","2.2u","0603","soc",40,56,passive("SOC_AVCC","GND"),note="V851SX internal analog LDO output bypass")
    add(d,"C36","470n","0402","soc",40,58,passive("VRA1","GND"),note="V851SX analog reference bypass")
    add(d,"C37","100n","0402","soc",20.5,60,passive("SOC_LDO_1V8","GND"))
    bypass = [("3V3",5),("3V3",6),("1V8",7),("1V8",8),("CORE_0V93",9),("CORE_0V93",10),("CORE_0V93",11),("DRAM_1V5",12)]
    for idx,(rail,dy) in enumerate(bypass,14):
        slot=idx-14
        add(d,f"C{idx}","100n","0402","soc",40+(slot%2)*4,60+(slot//2)*3,passive(rail,"GND"),mpn="0402 100n X7R",lcsc="C1525")
    add(d,"J3","DEBUG POGO","HDR8","soc",44,72,{str(i+1):(n,net) for i,(n,net) in enumerate([("GND","GND"),("3V3","3V3"),("UART0_TX","UART0_TX"),("UART0_RX","UART0_RX"),("E907_TX","E907_TX"),("E907_RX","E907_RX"),("FEL_PC2","BOOT0"),("PWRON_N","PWRON_N")])},note="1.27mm production/debug pads")
    add(d,"SW6","FEL","SW_SIDE","soc",55,91,{"1":("FEL_PC2","BOOT0"),"2":("FEL_PC2","BOOT0"),"3":("GND","GND")},mpn="GT-TC072B-H045-L1",lcsc="C5117859",rotation=90,note="Recessed recovery switch; straps PC2 low")
    add(d,"R10","10k","0402","soc",47,91,passive("3V3","BOOT0"))
    add(d,"R28","10k","0402","soc",44,91,passive("3V3","BOOT1"),note="PC3 BOOT1 pull-up; BOOT_SEL=11 TF first")

    lis={"1":("SCL","I2C0_SCL"),"2":("CS","RTC_3V3"),"3":("SDO_SA0",None),"4":("SDA","I2C0_SDA"),"5":("NC",None),"6":("GND","GND"),"7":("RES","GND"),"8":("GND","GND"),"9":("VDD","RTC_3V3"),"10":("VDDIO","RTC_3V3"),"11":("INT2",None),"12":("INT1","ACCEL_INT_N")}
    add(d,"U4","LIS2DW12TR","LGA-12","sensors",8,19,lis,mpn="LIS2DW12TR",lcsc="C189624",datasheet="https://www.st.com/resource/en/datasheet/lis2dw12.pdf")
    rtc={"1":("CLKOUT",None),"2":("INT","RTC_INT_N"),"3":("SCL","I2C0_SCL"),"4":("SDA","I2C0_SDA"),"5":("VSS","GND"),"6":("VBACKUP","RTC_VBACKUP"),"7":("VDD","RTC_3V3"),"8":("EVI","RTC_EVI")}
    add(d,"U5","RV-3028-C7","RTC-8","sensors",15,19,rtc,mpn="RV-3028-C7-32.768kHz-1ppm-TA-QC",lcsc="C3019759",datasheet="https://www.microcrystal.com/fileadmin/Media/Products/RTC/App.Manual/RV-3028-C7_App-Manual.pdf")
    # SN74LVC1G123DCTR (DCT / SM8): 1=Q, 2=GND, 3=Cext, 4=Rext/Cext, 5=A, 6=B, 7=CLR, 8=VCC.
    mono={"1":("Q","WAKE_PULSE"),"2":("GND","GND"),"3":("CEXT","WAKE_CEXT"),"4":("REXT_CEXT","WAKE_REXT"),"5":("A","WAKE_REQ_N"),"6":("B","RTC_3V3"),"7":("CLR","RTC_3V3"),"8":("VCC","RTC_3V3")}
    add(d,"U6","SN74LVC1G123DCTR","SSOP-8","sensors",24,19,mono,mpn="SN74LVC1G123DCTR",datasheet="https://www.ti.com/lit/ds/symlink/sn74lvc1g123.pdf")
    add(d,"Q1","2N7002","SOT23-3","sensors",32,19,{"1":("G","WAKE_PULSE"),"2":("S","GND"),"3":("D","PWRON_N")},mpn="2N7002",lcsc="C8545")
    add(d,"Q2","2N7002","SOT23-3","sensors",38,19,{"1":("G","WAKE_PULSE"),"2":("S","GND"),"3":("D","WAKE_PULSE_N")},mpn="2N7002",lcsc="C8545")
    add(d,"R11","10k","0402","sensors",10,24,passive("RTC_3V3","WAKE_REQ_N"))
    add(d,"R12","820k","0402","sensors",24,24,passive("RTC_3V3","WAKE_REXT"))
    add(d,"C23","100n","0402","sensors",28,24,passive("WAKE_REXT","WAKE_CEXT"))
    add(d,"R13","10k","0402","sensors",15,24,passive("RTC_VBACKUP","GND"))
    add(d,"R14","10k","0402","sensors",17,24,passive("RTC_EVI","GND"))
    add(d,"R15","4.7k","0402","sensors",8,27,passive("3V3","I2C0_SCL"))
    add(d,"R16","4.7k","0402","sensors",10,27,passive("3V3","I2C0_SDA"))
    add(d,"R17","10k","0402","sensors",12,27,passive("3V3","RTC_INT_N"))
    add(d,"R18","10k","0402","sensors",14,27,passive("3V3","ACCEL_INT_N"))
    # Open-drain wake sources share the always-on request node through small-signal diodes.
    add(d,"D2","BAT54","D_SOD123","sensors",17,28,passive("RTC_INT_N","WAKE_REQ_N"),rotation=90)
    add(d,"D3","BAT54","D_SOD123","sensors",21,28,passive("ACCEL_INT_N","WAKE_REQ_N"),rotation=90)
    add(d,"C24","100n","0402","sensors",8,31,passive("RTC_3V3","GND"),lcsc="C1525")
    add(d,"C25","100n","0402","sensors",15,31,passive("RTC_3V3","GND"),lcsc="C1525")
    add(d,"C26","100n","0402","sensors",24,31,passive("RTC_3V3","GND"),lcsc="C1525")

    # KD024EGOIN152-01 (RM690B0): Molex 502598-4591 45-pin, MIPI 1-lane, IM1/IM0=00.
    # MCU RGB bus (18-29) left NC. Host DSI lane1 unused. EL±/SWIRE await OLED PMIC (not invented).
    kd024 = {str(i): (f"PIN{i}", None) for i in range(1, 46)}
    kd024.update({
        "1": ("GND", "GND"), "2": ("GND", "GND"),
        "3": ("ELVSS", "ELVSS"), "4": ("ELVSS", "ELVSS"),
        "5": ("GND", "GND"),
        "6": ("ELVDD", "ELVDD"), "7": ("ELVDD", "ELVDD"),
        "8": ("GND", "GND"),
        "9": ("VCI", "LCD_3V3"),
        "10": ("GND", "GND"),
        "11": ("VDDIO", "LCD_1V8"),
        "12": ("GND", "GND"),
        "13": ("TE1", None),  # Optional panel status output unused in first bring-up.
        "14": ("SWIRE", "LCD_SWIRE"),
        "15": ("TE", "LCD_TE"),
        "16": ("RESX", "LCD_RST"),
        "17": ("GND", "GND"),
        # 18-29: MCU/RGB — NC in MIPI mode
        "30": ("GND", "GND"),
        "31": ("IM1", "GND"),
        "32": ("IM0", "GND"),
        "33": ("GND", "GND"), "34": ("GND", "GND"),
        "35": ("D0P", "DSI_D0P"), "36": ("D0N", "DSI_D0N"),
        "37": ("GND", "GND"), "38": ("GND", "GND"),
        "39": ("CLKP", "DSI_CKP"), "40": ("CLKN", "DSI_CKN"),
        "41": ("GND", "GND"), "42": ("GND", "GND"),
        "43": ("MTP", "GND"),
        "44": ("GND", "GND"), "45": ("GND", "GND"),
    })
    kd024.update({"MP1": ("MOUNT", "GND"), "MP2": ("MOUNT", "GND")})
    add(d, "J4", "KD024EGOIN152-01", "FPC45", "interfaces", 30, 39, kd024,
        mpn="502598-4593", lcsc="",
        datasheet="kd024_screen/KD024EGOIN152-01_engineering_spec.md",
        note="Molex 502598-4593; verify -4591 module FPC compatibility; MIPI 1-lane; EL± from U10")
    # TFT-only U7/L4/D4/R19/C27/C28 removed from the AMOLED variant.
    # VCI (3.3) gated by LCD_EN; VDDIO (1.8) via 0R from ALDO1 1V8.
    add(d, "U8", "TPS22918DBVR", "SOT23-6", "interfaces", 20, 40,
        {"1": ("VIN", "3V3"), "2": ("GND", "GND"), "3": ("ON", "LCD_EN"), "4": ("CT", None), "5": ("QOD", None), "6": ("VOUT", "LCD_3V3")},
        mpn="TPS22918DBVR", datasheet="https://www.ti.com/lit/ds/symlink/tps22918.pdf",
        note="Gates KD024 VCI. CT/QOD open OK.")
    add(d, "C29", "4.7u", "0603", "interfaces", 16, 40, passive("LCD_3V3", "GND"))
    add(d, "C42", "1u", "0603", "interfaces", 14, 40, passive("LCD_3V3", "GND"), note="VCI local")
    add(d, "C43", "100n", "0402", "interfaces", 12, 40, passive("LCD_3V3", "GND"), note="VCI HF")
    add(d, "R29", "0R", "0402", "interfaces", 20, 46, passive("1V8", "LCD_1V8"), note="VDDIO feed; swap for load-switch later if needed")
    add(d, "C44", "1u", "0603", "interfaces", 24, 46, passive("LCD_1V8", "GND"), note="VDDIO local")
    add(d, "C45", "100n", "0402", "interfaces", 26, 46, passive("LCD_1V8", "GND"), note="VDDIO HF")
    # EL bias: TPS65631DPDR (LCSC C165127). Defaults ELVDD=4.6 / ELVSS=-4.0 (within KD024 max).
    # CTRL shares LCD_EN (host enable). Panel SWIRE left open by default (RM690B0 allows NC); R31 0R DNP to join later.
    # VIN max 4.5 V — feed from VSYS; do not exceed during charge.
    tps65631 = {
        "1": ("SWP", "EL_SWP"),
        "2": ("PGND", "GND"),
        "3": ("OUTP", "ELVDD"),
        "4": ("FBS", "ELVDD"),
        "5": ("AGND", "GND"),
        "6": ("GND", "GND"),
        "7": ("CTRL", "LCD_EN"),
        "8": ("CT", "EL_CT"),
        "9": ("OUTN", "ELVSS"),
        "10": ("SWN", "EL_SWN"),
        "11": ("AVIN", "VSYS"),
        "12": ("PVIN", "VSYS"),
        "13": ("EPAD", "GND"),
    }
    add(d, "U10", "TPS65631DPDR", "WSON-12", "interfaces", 38, 36, tps65631,
        mpn="TPS65631DPDR", lcsc="C165127",
        datasheet="https://www.ti.com/lit/ds/symlink/tps65631.pdf",
        note="AMOLED EL± bias; CTRL shares VCI enable; default 4.6/-4.0 requires panel approval; no CTRL pulses")
    add(d, "L5", "4.7uH", "IND_2x2", "interfaces", 32, 32, passive("VSYS", "EL_SWP"), mpn="4.7uH 1.5A", note="ELVDD boost")
    add(d, "L6", "4.7uH", "IND_2x2", "interfaces", 44, 32, passive("EL_SWN", "GND"), mpn="4.7uH 1.5A", note="ELVSS IBB L to GND per TPS65631 app")
    add(d, "C46", "10u", "0603", "interfaces", 34, 28, passive("VSYS", "GND"), note="EL VIN")
    add(d, "C47", "10u", "0603", "interfaces", 36, 28, passive("VSYS", "GND"), note="EL VIN")
    add(d, "C48", "10u", "0603", "interfaces", 34, 36, passive("ELVDD", "GND"), note="ELVDD cout")
    add(d, "C49", "10u", "0603", "interfaces", 42, 36, passive("ELVSS", "GND"), note="ELVSS cout")
    add(d, "C50", "10u", "0603", "interfaces", 44, 36, passive("ELVSS", "GND"), note="ELVSS cout")
    add(d, "C51", "100n", "0402", "interfaces", 40, 40, passive("EL_CT", "GND"), note="VNEG transition CT")
    add(d, "R31", "0R", "0402", "interfaces", 40, 44, passive("LCD_SWIRE", "LCD_EN"), dnp=True,
        note="DNP required: shared CTRL/VCI enable; do not bridge or pulse until control topology reviewed")
    sd={"1":("DAT2","SD_D2"),"2":("DAT3","SD_D3"),"3":("CMD","SD_CMD"),"4":("VDD","SD_3V3"),"5":("CLK","SD_CLK"),"6":("VSS","GND"),"7":("DAT0","SD_D0"),"8":("DAT1","SD_D1"),"9":("CD","SD_DET"),"10":("SH","GND"),"11":("SH","GND"),"12":("SH","GND"),"13":("SH","GND")}
    add(d,"J5","MicroSD","MICROSD","interfaces",29,7,sd,mpn="MUP-M617-2",lcsc="C5205359")
    add(d,"Q3","AO3401A","SOT23-3","interfaces",41,8,{"1":("G","SD_PWR_GATE"),"2":("S","3V3"),"3":("D","SD_3V3")},mpn="AO3401A",lcsc="C15127")
    add(d,"R20","100k","0402","interfaces",45,8,passive("3V3","SD_PWR_GATE"))
    add(d,"R21","10k","0402","interfaces",49,8,passive("SD_PWR_EN","SD_PWR_GATE"))
    add(d,"C30","10u","0603","interfaces",39,12,passive("SD_3V3","GND"))
    for idx,(net,x) in enumerate([("SD_D2",36),("SD_D3",38.2),("SD_CMD",40.4),("SD_CLK",42.6),("SD_D0",44.8),("SD_D1",47.0),("SD_DET",49.2)],6):
        add(d,f"D{idx}","PESD4V0","0402","interfaces",x,15,passive(net,"GND"),mpn="PESD4V0Y1BBSF",rotation=270)
    for i,name,y in [(1,"UP",30),(2,"DOWN",40),(3,"OK",30),(4,"BACK",40)]:
        x=3 if i<3 else 55
        add(d,f"SW{i}",name,"SW_SIDE","interfaces",x,y,{"1":("KEY",f"KEY_{name}"),"2":("KEY",f"KEY_{name}"),"3":("GND","GND")},mpn="GT-TC072B-H045-L1",lcsc="C5117859",rotation=90 if i<3 else 270)
    add(d,"R22","100k","0402","interfaces",47,50,passive("1V8","ADC_KEYS"))
    add(d,"R23","0R","0402","interfaces",49,50,passive("KEY_UP","ADC_KEYS"))
    add(d,"R24","22k","0402","interfaces",51,50,passive("KEY_DOWN","ADC_KEYS"))
    add(d,"R25","47k","0402","interfaces",53,50,passive("KEY_OK","ADC_KEYS"))
    add(d,"R26","100k","0402","interfaces",55,50,passive("KEY_BACK","ADC_KEYS"))
    add(d,"C31","10n","0402","interfaces",45,50,passive("ADC_KEYS","GND"))
    add(d,"D5","STATUS","LED0603","interfaces",45,55,passive("STATUS_LED_A","GND"),mpn="0603 Blue LED")
    add(d,"R27","2.2k","0402","interfaces",42,52,passive("STATUS_LED","STATUS_LED_A"))
    display_placement = {
        "J4": (30, 39, 0), "U10": (46, 30, 0),
        "L5": (41.5, 28, 0), "L6": (50.5, 28, 0),
        "C46": (46, 25.5, 0), "C47": (49, 25.5, 0),
        "C48": (42, 31.5, 90), "C49": (50, 31.5, 90),
        "C50": (52, 34, 90), "C51": (48.5, 34.5, 0),
        "C42": (25, 42, 90), "C43": (27, 42, 90),
        "C44": (30, 42, 90), "C45": (32, 42, 90),
        "R29": (30, 45, 0), "R31": (35, 42, 0),
    }
    for dev in d:
        if dev.ref in display_placement:
            dev.x, dev.y, dev.rotation = display_placement[dev.ref]
    return d


def pin_type(dev: Device, num: str) -> str:
    name, net = dev.pins[num]
    if dev.ref == "U2":
        if num in {"14", "48", "50"}: return "power_out"
        if name.startswith(("VCC", "VDD")) or num in {"51", "89"}: return "power_in"
        if num in {"15", "25", "43", "56", "57", "59", "60", "61"}: return "output"
        if num in {"16", "23", "24", "30", "31", "42", "46", "58"}: return "input"
        return "bidirectional"
    if dev.ref == "U1":
        if num in {"1", "29", "38"}: return "open_collector"
        if num in {"3", "6", "7", "13", "17", "23", "24", "33", "37", "41"}: return "power_in"
        if num in {"2", "5", "8", "18", "22", "28", "34"}: return "power_out"
        if num in {"4", "9", "21", "30", "31", "40"}: return "input"
        if num == "39": return "bidirectional"
    return "passive"


def symbol_library_entry(dev: Device) -> str:
    pin_items = sorted(dev.pins.items(), key=lambda kv: (not kv[0].isdigit(), int(kv[0]) if kv[0].isdigit() else kv[0]))
    nleft = (len(pin_items) + 1) // 2
    pitch = 2.54
    half_h = max(5.08, (nleft - 1) * pitch / 2 + 1.27)
    lines = [f'\t\t(symbol {q("Sameat:" + dev.ref + "_" + dev.value)}', '\t\t\t(pin_names (offset 0.8))', '\t\t\t(exclude_from_sim no)', '\t\t\t(in_bom yes)', '\t\t\t(on_board yes)']
    for key,val in [("Reference",dev.ref[0]),("Value",dev.value),("Footprint",f"Sameat:{dev.footprint}"),("Datasheet",dev.datasheet),("Description",dev.note or dev.mpn)]:
        lines += [f'\t\t\t(property {q(key)} {q(val)}', '\t\t\t\t(at 0 0 0)', '\t\t\t\t(effects (font (size 1.0 1.0)) (hide yes))', '\t\t\t)']
    lines += [f'\t\t\t(symbol {q(dev.ref + "_" + dev.value + "_0_1")}', f'\t\t\t\t(rectangle (start -12.7 {-half_h:.3f}) (end 12.7 {half_h:.3f}) (stroke (width 0.254) (type default)) (fill (type background)))', '\t\t\t)']
    lines += [f'\t\t\t(symbol {q(dev.ref + "_" + dev.value + "_1_1")}']
    for idx,(num,(name,_net)) in enumerate(pin_items):
        if idx < nleft:
            yy = -((nleft - 1) * pitch / 2) + idx * pitch
            at = f'-15.24 {yy:.3f} 0'
        else:
            j=idx-nleft; nr=len(pin_items)-nleft
            yy = -((nr - 1) * pitch / 2) + j * pitch
            at = f'15.24 {yy:.3f} 180'
        lines += [f'\t\t\t\t(pin {pin_type(dev,num)} line (at {at}) (length 2.54)', f'\t\t\t\t\t(name {q(name)} (effects (font (size .8 .8))))', f'\t\t\t\t\t(number {q(num)} (effects (font (size .8 .8))))', '\t\t\t\t)']
    lines += ['\t\t\t)', '\t\t)']
    return "\n".join(lines)


def supply_source_symbol() -> str:
    return '(symbol "Sameat:SUPPLY_SOURCE" (power) (pin_names (offset 0)) (in_bom no) (on_board no) (property "Reference" "#FLG" (at 0 0 0) (effects (font (size 1 1)) (hide yes))) (property "Value" "SUPPLY_SOURCE" (at 0 2.54 0) (effects (font (size 1 1)) (hide yes))) (symbol "SUPPLY_SOURCE_0_1" (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.27 1.27) (xy 0 2.54) (xy 1.27 1.27) (xy 0 1.27)) (stroke (width 0) (type default)) (fill (type none)))) (symbol "SUPPLY_SOURCE_1_1" (pin power_out line (at 0 0 90) (length 0) (name "pwr" (effects (font (size 1 1)))) (number "1" (effects (font (size 1 1)))))))'


def schematic_for_sheet(sheet: str, devs: list[Device], root_uuid: str, sheet_uuid: str) -> str:
    suid=uid(f"schematic-{sheet}")
    title={"power":"01 Power / Charger / PMIC","soc":"02 V851s / Boot / Storage","sensors":"03 Always-on Sensors / Wake","interfaces":"04 Display / SD / Buttons"}[sheet]
    selected=[d for d in devs if d.sheet==sheet]
    out=['(kicad_sch','\t(version 20250114)','\t(generator "sameat-evt1-r1")','\t(generator_version "r1")',f'\t(uuid {q(suid)})','\t(paper "A2")', '\t(title_block', f'\t\t(title {q(title)})','\t\t(date "2026-09-05")','\t\t(rev "EVT1-minboot-r1")','\t\t(company "Sameat")','\t\t(comment 1 "Reference-derived engineering validation design")','\t\t(comment 2 "NOT physically validated; review before fabrication")','\t)', '\t(lib_symbols']
    out += [symbol_library_entry(d) for d in selected]
    out += [supply_source_symbol()]
    out += ['\t)']
    # Wide grid; the V851s block receives an entire column.
    placements: dict[str,tuple[float,float]]={}
    large=[d for d in selected if len(d.pins)>30]
    small=[d for d in selected if d not in large]
    for i,dv in enumerate(small):
        placements[dv.ref]=(round((40+(i%3)*70)/1.27)*1.27,round((30+(i//3)*26)/1.27)*1.27)
    for i,dv in enumerate(large):
        placements[dv.ref]=(304.8,139.7+i*100)
    for dev in selected:
        x,y=placements[dev.ref]
        pin_items=sorted(dev.pins.items(), key=lambda kv:(not kv[0].isdigit(), int(kv[0]) if kv[0].isdigit() else kv[0]))
        nleft=(len(pin_items)+1)//2; pitch=2.54
        duid=uid(f"symbol-{dev.ref}")
        out += ['\t(symbol',f'\t\t(lib_id {q("Sameat:" + dev.ref + "_" + dev.value)})',f'\t\t(at {x:.3f} {y:.3f} 0)','\t\t(unit 1)','\t\t(exclude_from_sim no)','\t\t(in_bom yes)','\t\t(on_board yes)',f'\t\t(dnp {"yes" if dev.dnp else "no"})',f'\t\t(uuid {q(duid)})']
        half_h=max(5.08,(nleft-1)*pitch/2+1.27)
        for key,val,px,py,hide in [("Reference",dev.ref,x,y-half_h-4,False),("Value",dev.value,x,y-half_h-2,False),("Footprint",f"Sameat:{dev.footprint}",x,y,True),("Datasheet",dev.datasheet,x,y,True),("MPN",dev.mpn,x,y,True),("LCSC",dev.lcsc,x,y,True),("Description",dev.note,x,y,True)]:
            out += [f'\t\t(property {q(key)} {q(val)}',f'\t\t\t(at {px:.3f} {py:.3f} 0)',f'\t\t\t(effects (font (size 1 1)){" (hide yes)" if hide else ""})','\t\t)']
        for num,_ in pin_items: out += [f'\t\t(pin {q(num)} (uuid {q(uid(f"pin-{dev.ref}-{num}"))}))']
        out += ['\t\t(instances',f'\t\t\t(project {q("portable_display_epass")}',f'\t\t\t\t(path {q("/"+root_uuid+"/"+sheet_uuid)} (reference {q(dev.ref)}) (unit 1))','\t\t\t)','\t\t)','\t)']
        for idx,(num,(_name,net)) in enumerate(pin_items):
            if idx<nleft:
                yy=y+((nleft-1)*pitch/2)-idx*pitch; xx=x-15.24; orient=180
            else:
                j=idx-nleft; nr=len(pin_items)-nleft
                yy=y+((nr-1)*pitch/2)-j*pitch; xx=x+15.24; orient=0
            if net:
                out += [f'\t(global_label {q(net)} (shape passive) (at {xx:.3f} {yy:.3f} {orient}) (effects (font (size .8 .8)) (justify {"right" if orient==180 else "left"})) (uuid {q(uid(f"label-{dev.ref}-{num}"))}))']
            else:
                out += [f'\t(no_connect (at {xx:.3f} {yy:.3f}) (uuid {q(uid(f"nc-{dev.ref}-{num}"))}))']
    if sheet == "power":
        for idx,net in enumerate(("GND","VBUS","VBAT","3V3","CORE_0V93","DRAM_1V5")):
            ref="#FLG"+str(idx+1); x=254.0+idx*20.32; y=254.0
            out += [f'(symbol (lib_id "Sameat:SUPPLY_SOURCE") (at {x} {y} 0) (unit 1) (in_bom no) (on_board no) (dnp no) (uuid "{uid(ref)}") (property "Reference" "{ref}" (at {x} {y-2.54} 0) (effects (font (size 1 1)) (hide yes))) (property "Value" "SUPPLY_SOURCE" (at {x} {y-5.08} 0) (effects (font (size 1 1)) (hide yes))) (instances (project "portable_display_epass" (path "/{root_uuid}/{sheet_uuid}" (reference "{ref}") (unit 1)))))']
            out += [f'(global_label "{net}" (shape passive) (at {x} {y} 0) (effects (font (size 1 1)) (justify left)) (uuid "{uid(ref+"-label")}"))']
    out += ['\t(embedded_fonts no)',')']
    return "\n".join(out)+"\n"


def root_schematic() -> tuple[str, dict[str,str]]:
    root_uuid=uid("root-schematic")
    sheets={name:uid(f"root-sheet-{name}") for name in ("power","soc","sensors","interfaces")}
    out=['(kicad_sch','\t(version 20250114)','\t(generator "sameat-evt1-r1")','\t(generator_version "r1")',f'\t(uuid {q(root_uuid)})','\t(paper "A4")','\t(title_block','\t\t(title "Portable Display ePass")','\t\t(date "2026-09-05")','\t\t(rev "EVT1-minboot-r1")','\t\t(company "Sameat")','\t\t(comment 1 "V851s + AXP2101; display=KD024EGOIN152-01 (RM690B0) wiring started; EL PMIC TBD")','\t\t(comment 2 "EVT design: not physically validated")','\t)','\t(lib_symbols)']
    info=[("power","01_power.kicad_sch",25,35),("soc","02_soc_v851s.kicad_sch",100,35),("sensors","03_sensors.kicad_sch",25,95),("interfaces","04_interfaces.kicad_sch",100,95)]
    for page,(name,file,x,y) in enumerate(info,2):
        su=sheets[name]
        out += ['\t(sheet',f'\t\t(at {x} {y})','\t\t(size 55 35)','\t\t(exclude_from_sim no)','\t\t(in_bom yes)','\t\t(on_board yes)','\t\t(dnp no)', '\t\t(stroke (width .1524) (type solid))','\t\t(fill (color 0 0 0 0))',f'\t\t(uuid {q(su)})',f'\t\t(property "Sheetname" {q(name.upper())} (at {x} {y-1} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))',f'\t\t(property "Sheetfile" {q(file)} (at {x} {y+36} 0) (effects (font (size 1.27 1.27)) (justify left top)))',f'\t\t(instances (project "portable_display_epass" (path "/{root_uuid}" (page "{page}"))))','\t)']
    pages=" ".join(f'(path {q("/"+sheets[name])} (page "{i+2}"))' for i,name in enumerate(("power","soc","sensors","interfaces")))
    out += ['\t(text "EVT1-minboot-r1 - engineering candidate; NOT FOR FABRICATION\\nNo radio / no audio / no touch; KD024 AOD firmware pending\\nSee docs/ for pin map, power tree and bring-up checklist." (exclude_from_sim no) (at 25 150 0) (effects (font (size 1.27 1.27)) (justify left top)) (uuid "'+uid('root-note')+'"))','\t(sheet_instances (path "/" (page "1")))','\t(embedded_fonts no)',')']
    return "\n".join(out)+"\n",sheets


def write_local_footprints(devs: list[Device]) -> None:
    LIB.mkdir(exist_ok=True)
    kinds={d.footprint:d.pads for d in devs}
    for name,pads in kinds.items():
        if name in {"FPC45", "WSON-12"}:
            continue  # Curated local footprints; see docs/DISPLAY_FOOTPRINT_REVIEW.md
        x0=min(p.x-p.sx/2 for p in pads)-.1; x1=max(p.x+p.sx/2 for p in pads)+.1
        y0=min(p.y-p.sy/2 for p in pads)-.1; y1=max(p.y+p.sy/2 for p in pads)+.1
        lines=[f'(footprint {q(name)}','\t(version 20240108)','\t(generator "sameat-evt1-generator")','\t(layer "F.Cu")',f'\t(property "Reference" "REF**" (at 0 {y0-1:.3f} 0) (layer "F.SilkS") (hide yes) (effects (font (size 1 1) (thickness .15))))',f'\t(property "Value" {q(name)} (at 0 {y1+1:.3f} 0) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))','\t(attr smd)',f'\t(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))',f'\t(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))','\t(fp_text user "${REFERENCE}" (at 0 0 0) (layer "F.Fab") (effects (font (size .7 .7) (thickness .1))))']
        for i,p in enumerate(pads):
            layer=' '.join(q(x) for x in p.layers)
            if p.kind=="thru_hole":
                lines.append(f'\t(pad {q(p.number)} thru_hole {p.shape} (at {p.x:.4f} {p.y:.4f} {p.angle:g}) (size {p.sx:.4f} {p.sy:.4f}) (drill {p.drill or .3:.4f}) (layers {layer}))')
            else:
                rr=' (roundrect_rratio .2)' if p.shape=='roundrect' else ''
                lines.append(f'\t(pad {q(p.number)} smd {p.shape} (at {p.x:.4f} {p.y:.4f} {p.angle:g}) (size {p.sx:.4f} {p.sy:.4f}) (layers {layer}){rr})')
        lines.append(')')
        (LIB/f"{name}.kicad_mod").write_text("\n".join(lines)+"\n")


def abs_pad(dev: Device, pad: Pad) -> tuple[float,float]:
    a=math.radians(dev.rotation); ca,sa=math.cos(a),math.sin(a)
    return dev.x+pad.x*ca+pad.y*sa, dev.y-pad.x*sa+pad.y*ca


def _seg(x1,y1,x2,y2,width,layer,net,net_ids,tag) -> str:
    identity=f"seg-{tag}-{x1:.5f}-{y1:.5f}-{x2:.5f}-{y2:.5f}-{width:.4f}-{layer}-{net}"
    return f'\t(segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (width {width:.3f}) (layer {q(layer)}) (net {net_ids[net]}) (uuid {q(uid(identity))}))'


def _circle_rect_clear(cx,cy,cr,x0,y0,x1,y1) -> float:
    qx=min(max(cx,x0),x1); qy=min(max(cy,y0),y1)
    return math.hypot(cx-qx,cy-qy)-cr


def _segments_cross(ax,ay,bx,by,cx,cy,dx,dy) -> bool:
    def orient(px,py,qx,qy,rx,ry):
        v=(qy-py)*(rx-qx)-(qx-px)*(ry-qy)
        if abs(v)<1e-12:
            return 0
        return 1 if v>0 else -1
    o1=orient(ax,ay,bx,by,cx,cy); o2=orient(ax,ay,bx,by,dx,dy)
    o3=orient(cx,cy,dx,dy,ax,ay); o4=orient(cx,cy,dx,dy,bx,by)
    return o1!=0 and o2!=0 and o3!=0 and o4!=0 and o1!=o2 and o3!=o4


def _seg_seg_dist(ax,ay,bx,by,cx,cy,dx,dy) -> float:
    if _segments_cross(ax,ay,bx,by,cx,cy,dx,dy):
        return 0.0
    return min(
        _point_seg_dist(ax,ay,cx,cy,dx,dy),
        _point_seg_dist(bx,by,cx,cy,dx,dy),
        _point_seg_dist(cx,cy,ax,ay,bx,by),
        _point_seg_dist(dx,dy,ax,ay,bx,by),
    )


def _seg_aabb_dist(x1,y1,x2,y2,a0,b0,a1,b1) -> float:
    d=_point_seg_dist(a0,b0,x1,y1,x2,y2)
    d=min(d,_point_seg_dist(a1,b0,x1,y1,x2,y2))
    d=min(d,_point_seg_dist(a0,b1,x1,y1,x2,y2))
    d=min(d,_point_seg_dist(a1,b1,x1,y1,x2,y2))
    d=min(d,_point_seg_dist(x1,y1,a0,b0,a1,b0))
    d=min(d,_point_seg_dist(x1,y1,a0,b1,a1,b1))
    d=min(d,_point_seg_dist(x1,y1,a0,b0,a0,b1))
    d=min(d,_point_seg_dist(x1,y1,a1,b0,a1,b1))
    d=min(d,_point_seg_dist(x2,y2,a0,b0,a1,b0))
    d=min(d,_point_seg_dist(x2,y2,a0,b1,a1,b1))
    d=min(d,_point_seg_dist(x2,y2,a0,b0,a0,b1))
    d=min(d,_point_seg_dist(x2,y2,a1,b0,a1,b1))
    # If either endpoint is inside the rectangle the distance is zero.
    for px,py in ((x1,y1),(x2,y2)):
        if a0-1e-9<=px<=a1+1e-9 and b0-1e-9<=py<=b1+1e-9:
            return 0.0
    return d


def _point_seg_dist(px,py,x1,y1,x2,y2) -> float:
    vx,vy=x2-x1,y2-y1
    l2=vx*vx+vy*vy
    if l2<1e-12:
        return math.hypot(px-x1,py-y1)
    t=max(0.0,min(1.0,((px-x1)*vx+(py-y1)*vy)/l2))
    return math.hypot(px-(x1+t*vx), py-(y1+t*vy))


HOLE_CLEAR = 0.25


class CopperMap:
    def __init__(self, devs: list[Device]):
        self.pads=[]  # (x0,y0,x1,y1,net,ref,pn)
        self.vias: list[tuple[float,float,float,str]]=[]  # x,y,radius,net
        self.tracks: list[tuple[float,float,float,float,float,str]]=[]  # x1,y1,x2,y2,width,net
        for d in devs:
            for p in d.pads:
                px,py=abs_pad(d,p)
                net=d.pins.get(p.number,("",None))[1]
                self.pads.append((px-p.sx/2,py-p.sy/2,px+p.sx/2,py+p.sy/2,net or "",d.ref,p.number))
                if p.kind=="thru_hole":
                    self.vias.append((px,py,max(p.sx,p.sy)/2,net or ""))

    def via_ok(self, x: float, y: float, net: str) -> tuple[bool,str]:
        if x<1.2 or y<1.2 or x>56.8 or y>108.8:
            return False, f"outside board at ({x:.2f},{y:.2f})"
        vr=VIA_SIZE/2
        hr=VIA_DRILL/2
        for vx,vy,rr,n2 in self.vias:
            dist=math.hypot(x-vx,y-vy)
            if n2!=net:
                # Hole of new via to other via copper, and vice versa.
                if dist-hr-rr < HOLE_CLEAR:
                    return False, f"hole-to-via {dist-hr-rr:.3f} mm vs {n2} at ({vx:.2f},{vy:.2f})"
                if dist < vr+rr+HD_CLEAR:
                    return False, f"via copper vs {n2} at ({vx:.2f},{vy:.2f})"
            elif dist<VIA_SIZE+0.05:
                return False, f"stacked via on {net}"
        for x0,y0,x1,y1,n2,ref,pn in self.pads:
            gap=_circle_rect_clear(x,y,vr,x0,y0,x1,y1)
            hole_gap=_circle_rect_clear(x,y,hr,x0,y0,x1,y1)
            if n2==net:
                if hole_gap<0.05:
                    return False, f"via on own pad {ref}.{pn}"
                continue
            if gap<HD_CLEAR:
                return False, f"via-pad clearance {gap:.3f} mm to {ref}.{pn}[{n2}]"
            if hole_gap<HOLE_CLEAR:
                return False, f"hole-to-pad {hole_gap:.3f} mm to {ref}.{pn}[{n2}]"
        for x1,y1,x2,y2,w,n2 in self.tracks:
            if n2==net:
                continue
            d=_point_seg_dist(x,y,x1,y1,x2,y2)
            if d-hr-w/2 < HOLE_CLEAR:
                return False, f"hole-to-track {d-hr-w/2:.3f} mm vs {n2}"
            if d-vr-w/2 < HD_CLEAR:
                return False, f"via-to-track {d-vr-w/2:.3f} mm vs {n2}"
        return True, "ok"

    def track_ok(self, x1,y1,x2,y2,width,net) -> tuple[bool,str]:
        hr=VIA_DRILL/2
        for x0,y0,x3,y3,n2,ref,pn in self.pads:
            if n2==net:
                continue
            d=_seg_aabb_dist(x1,y1,x2,y2,x0,y0,x3,y3)
            if d-width/2 < HD_CLEAR:
                return False, f"track-pad {d-width/2:.3f} mm vs {ref}.{pn}[{n2}]"
        for vx,vy,rr,n2 in self.vias:
            if n2==net:
                continue
            d=_point_seg_dist(vx,vy,x1,y1,x2,y2)
            if d-hr-width/2 < HOLE_CLEAR:
                return False, f"track hole-clear {d-hr-width/2:.3f} mm vs via {n2} ({vx:.2f},{vy:.2f})"
            if d-rr-width/2 < HD_CLEAR:
                return False, f"track-via copper {d-rr-width/2:.3f} mm vs {n2}"
        for ax,ay,bx,by,w2,n2 in self.tracks:
            if n2==net:
                continue
            if _segments_cross(x1,y1,x2,y2,ax,ay,bx,by):
                return False, f"track crosses {n2}"
            d=_seg_seg_dist(x1,y1,x2,y2,ax,ay,bx,by)
            if d-(width+w2)/2 < HD_CLEAR:
                return False, f"track-track {d-(width+w2)/2:.3f} mm vs {n2}"
        return True, "ok"

    def add_via(self, x, y, net):
        self.vias.append((x,y,VIA_SIZE/2,net))

    def add_track(self, x1,y1,x2,y2,width,net):
        self.tracks.append((x1,y1,x2,y2,width,net))


def pad_outward(dev: Device, pad: Pad) -> tuple[float,float]:
    if abs(pad.x)>=abs(pad.y):
        return math.copysign(1,pad.x) if pad.x else 0.0, 0.0
    return 0.0, math.copysign(1,pad.y) if pad.y else -1.0


def deterministic_fanout_and_routes(devs: list[Device], net_ids: dict[str,int]) -> tuple[list[str],dict]:
    """Staggered V851s/AXP fanout plus explicit non-display routes. No maze."""
    copper=CopperMap(devs)
    items: list[str]=[]
    fanout_via: dict[tuple[str,str],tuple[float,float]]={}  # (ref,pin)->(x,y)
    report={"v851_ok":[], "v851_skip_display":[], "v851_nc":[], "v851_fail":[], "routes":{}}

    def place_via(net, x, y, tag):
        ok,why=copper.via_ok(x,y,net)
        if not ok:
            return False, why
        copper.add_via(x,y,net)
        items.append(_via(x,y,net,net_ids,tag))
        return True, "ok"

    def stub_and_via(dev: Device, pad: Pad, net: str, rings: tuple[float,...], ring_i: int, tag: str, force_dir=None):
        px,py=abs_pad(dev,pad)
        if force_dir:
            ux,uy=force_dir
        else:
            ux,uy=pad_outward(dev,pad)
        a=math.radians(dev.rotation); ca,sa=math.cos(a),math.sin(a)
        rx,ry=ux*ca+uy*sa, -ux*sa+uy*ca
        txd,tyd=-ry,rx  # along-side
        width=HD_WIDTH if dev.ref=="U2" else NORM_WIDTH
        guide=rings[ring_i%len(rings)]
        extra=() if ring_i%3!=2 else (3.90,4.20,4.50,4.80)
        radii=sorted({*rings, 1.20,1.50,1.80,2.10,2.40,2.70,3.00,3.30,3.60, *extra}, key=lambda r:(abs(r-guide), r))
        # Avoid along-side offsets that land on another QFN pad centre (n*0.35).
        tangs=(0.00,0.15,-0.15,0.22,-0.22,0.48,-0.48,0.55,-0.55,0.85,-0.85,1.15,-1.15,1.50,-1.50,1.85,-1.85)
        last_why="no candidate"
        for dist in radii:
            for tang in tangs:
                vx=px+rx*dist+txd*tang
                vy=py+ry*dist+tyd*tang
                ok,why=copper.via_ok(vx,vy,net)
                if not ok:
                    last_why=why
                    continue
                # Leave the pad already angled so the stub is not 0.35 mm
                # beside a neighbour hole for the whole radial run.
                jx,jy=px+rx*0.70+txd*tang, py+ry*0.70+tyd*tang
                segs=[(px,py,jx,jy),(jx,jy,vx,vy)]
                good=True
                for a,b,c,e in segs:
                    ok,why=copper.track_ok(a,b,c,e,width,net)
                    if not ok:
                        last_why=why
                        good=False
                        break
                if not good:
                    continue
                copper.add_via(vx,vy,net)
                for a,b,c,e in segs:
                    copper.add_track(a,b,c,e,width,net)
                    items.append(_seg(a,b,c,e,width,"F.Cu",net,net_ids,f"fo-{tag}-{a:.2f}"))
                items.append(_via(vx,vy,net,net_ids,f"fo-via-{tag}"))
                fanout_via[(dev.ref,pad.number)]=(vx,vy)
                return True, f"r={dist:.2f} t={tang:+.2f}"
        return False, last_why

    u2=next(d for d in devs if d.ref=="U2")
    work=[]
    for pad in u2.pads:
        net=u2.pins.get(pad.number,("",None))[1]
        name=u2.pins.get(pad.number,(pad.number,None))[0]
        if pad.number=="89":
            report["v851_nc"].append({"pin":pad.number,"name":name,"net":"GND-EP","note":"EP uses thermal vias"})
            continue
        if not net:
            report["v851_nc"].append({"pin":pad.number,"name":name,"net":None})
            continue
        if net in DISPLAY_NETS:
            report["v851_skip_display"].append({"pin":pad.number,"name":name,"net":net})
            continue
        work.append(pad)
    # Inner ring first so later outer-ring stubs can dogleg around known holes.
    work.sort(key=lambda p: (int(p.number)%3, int(p.number)))
    for pad in work:
        net=u2.pins[pad.number][1]
        name=u2.pins[pad.number][0]
        ring=int(pad.number)%3
        ok,why=stub_and_via(u2,pad,net,V851_RINGS,ring,f"U2-{pad.number}")
        rec={"pin":pad.number,"name":name,"net":net,"why":why}
        if not ok:
            px,py=abs_pad(u2,pad)
            ux,uy=pad_outward(u2,pad)
            a=math.radians(u2.rotation); ca,sa=math.cos(a),math.sin(a)
            rx,ry=ux*ca+uy*sa, -ux*sa+uy*ca
            txd,tyd=-ry,rx
            width=HD_WIDTH
            for dist in (1.6,1.9,2.2,2.5,2.8,3.1,3.4,3.7,4.0,4.4):
                for tang in (0.6,-0.6,0.9,-0.9,1.2,-1.2,1.5,-1.5,1.8,-1.8,2.1,-2.1):
                    vx,vy=px+rx*dist+txd*tang, py+ry*dist+tyd*tang
                    okv,whyv=copper.via_ok(vx,vy,net)
                    if not okv:
                        why=whyv
                        continue
                    jx,jy=px+rx*0.70+txd*tang, py+ry*0.70+tyd*tang
                    segs=[(px,py,jx,jy),(jx,jy,vx,vy)]
                    good=True
                    for a1,b1,c1,e1 in segs:
                        okt,whyt=copper.track_ok(a1,b1,c1,e1,width,net)
                        if not okt:
                            why=whyt
                            good=False
                            break
                    if not good:
                        continue
                    copper.add_via(vx,vy,net)
                    for a1,b1,c1,e1 in segs:
                        copper.add_track(a1,b1,c1,e1,width,net)
                        items.append(_seg(a1,b1,c1,e1,width,"F.Cu",net,net_ids,f"fo2-{pad.number}-{a1:.2f}"))
                    items.append(_via(vx,vy,net,net_ids,f"fo2-via-{pad.number}"))
                    fanout_via[("U2",pad.number)]=(vx,vy)
                    ok,why=True, f"retry r={dist:.2f} t={tang:+.2f}"
                    break
                if ok:
                    break
        rec={"pin":pad.number,"name":name,"net":net,"why":why}
        (report["v851_ok"] if ok else report["v851_fail"]).append(rec)

    u1=next(d for d in devs if d.ref=="U1")
    axp_rings=(1.00,1.70)
    for pad in u1.pads:
        net=u1.pins.get(pad.number,("",None))[1]
        if not net or pad.number=="41":
            continue
        stub_and_via(u1,pad,net,axp_rings,int(pad.number)%2,f"U1-{pad.number}")

    def fan_part(ref: str, rings=(0.90,1.40), skip_th=True):
        dev=next(d for d in devs if d.ref==ref)
        for pad in dev.pads:
            net=dev.pins.get(pad.number,("",None))[1]
            if not net or net in DISPLAY_NETS:
                continue
            if skip_th and pad.kind=="thru_hole":
                fanout_via[(dev.ref,pad.number)]=abs_pad(dev,pad)
                continue
            if (dev.ref,pad.number) in fanout_via:
                continue
            stub_and_via(dev,pad,net,rings,int(pad.number)%len(rings),f"{ref}-{pad.number}")

    for ref in ("J5","U9","J3","U4","U5","U6"):
        fan_part(ref)

    def via_of(ref, pin) -> tuple[float,float] | None:
        return fanout_via.get((ref,str(pin)))

    def manhattan(net, a, b, layer, width, tag):
        if a is None or b is None:
            report["routes"][tag]="missing fanout via"
            return False
        x1,y1=a; x2,y2=b
        mid=(x2,y1)
        items.append(_seg(x1,y1,mid[0],mid[1],width,layer,net,net_ids,tag+"-h"))
        items.append(_seg(mid[0],mid[1],x2,y2,width,layer,net,net_ids,tag+"-v"))
        report["routes"][tag]="ok"
        return True

    # Board-level buses are not emitted here: L-shaped B.Cu runs crossed the
    # staggered via field and shorted. Fanout vias remain the deliverable.
    report["routes"]["nand"]="fanout only; B.Cu trunk omitted (via-field shorts)"
    report["routes"]["sd"]="fanout only; B.Cu trunk omitted (via-field shorts)"
    report["routes"]["usb-pair"]="fanout only; pair trunk omitted (via-field / U9 pad shorts)"
    report["routes"]["i2c"]="fanout only"
    report["routes"]["uart"]="fanout only"
    report["routes"]["pmic"]="fanout only"

    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"fanout_report.json").write_text(json.dumps(report, indent=2))
    return items, report


def footprint_instance(dev: Device, net_ids: dict[str,int]) -> str:
    x0=min(p.x-p.sx/2 for p in dev.pads)-.1; x1=max(p.x+p.sx/2 for p in dev.pads)+.1
    y0=min(p.y-p.sy/2 for p in dev.pads)-.1; y1=max(p.y+p.sy/2 for p in dev.pads)+.1
    lines=[f'\t(footprint {q("Sameat:"+dev.footprint)}','\t\t(layer "F.Cu")',f'\t\t(at {dev.x:.4f} {dev.y:.4f} {dev.rotation:g})',f'\t\t(uuid {q(uid("fp-"+dev.ref))})',f'\t\t(property "Reference" {q(dev.ref)} (at 0 {y0-1:.3f} {dev.rotation:g}) (layer "F.SilkS") (hide yes) (effects (font (size 1 1) (thickness .15))))',f'\t\t(property "Value" {q(dev.value)} (at 0 {y1+1:.3f} {dev.rotation:g}) (layer "F.Fab") (effects (font (size .7 .7) (thickness .1))))',f'\t\t(property "MPN" {q(dev.mpn)} (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))',f'\t\t(property "LCSC" {q(dev.lcsc)} (at 0 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1))))',f'\t\t(path {q("/"+uid("root-schematic")+"/"+uid("root-sheet-"+dev.sheet)+"/"+uid("symbol-"+dev.ref))})',f'\t\t(attr smd{" dnp" if dev.dnp else ""})',f'\t\t(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width .1) (type default)) (fill none) (layer "F.Fab"))',f'\t\t(fp_rect (start {x0:.3f} {y0:.3f}) (end {x1:.3f} {y1:.3f}) (stroke (width .05) (type default)) (fill none) (layer "F.CrtYd"))',f'\t\t(fp_text user "${{REFERENCE}}" (at 0 0 {dev.rotation:g}) (layer "F.Fab") (effects (font (size .7 .7) (thickness .1))))']
    for p in dev.pads:
        net=dev.pins.get(p.number,("",None))[1]
        netstr=f' (net {net_ids[net]} {q(net)})' if net else ''
        fn=dev.pins.get(p.number,(p.number,None))[0]
        layers=' '.join(q(x) for x in p.layers)
        if p.kind=="thru_hole":
            lines.append(f'\t\t(pad {q(p.number)} thru_hole {p.shape} (at {p.x:.4f} {p.y:.4f} {(dev.rotation+p.angle)%360:g}) (size {p.sx:.4f} {p.sy:.4f}) (drill {p.drill or .3:.4f}) (layers {layers}){netstr} (pinfunction {q(fn)}) (pintype {q(pin_type(dev,p.number))}) (uuid {q(uid(f"pad-{dev.ref}-{p.number}-{p.x}-{p.y}"))}))')
        else:
            rr=' (roundrect_rratio .2)' if p.shape=='roundrect' else ''
            lines.append(f'\t\t(pad {q(p.number)} smd {p.shape} (at {p.x:.4f} {p.y:.4f} {(dev.rotation+p.angle)%360:g}) (size {p.sx:.4f} {p.sy:.4f}) (layers {layers}){rr}{netstr} (pinfunction {q(fn)}) (pintype {q(pin_type(dev,p.number))}) (uuid {q(uid(f"pad-{dev.ref}-{p.number}-{p.x}-{p.y}"))}))')
    lines.append('\t)')
    return "\n".join(lines)


@dataclass(frozen=True)
class Terminal:
    net: str
    x: float
    y: float
    radius: float = .30
    active: bool = True
    dx: float = 0.0
    dy: float = 0.0


def snap(value: float, grid: float = .1) -> float:
    return round(value / grid) * grid


def _via(x: float, y: float, net: str, net_ids: dict[str,int], tag: str) -> str:
    tag = f"via-{tag}-{x:.5f}-{y:.5f}-{net}"
    return f'\t(via (at {x:.4f} {y:.4f}) (size {VIA_SIZE:.2f}) (drill {VIA_DRILL:.2f}) (layers "F.Cu" "B.Cu") (net {net_ids[net]}) (uuid {q(uid(tag))}))'


def escape_fanout(devs: list[Device], net_ids: dict[str,int]) -> tuple[list[str],dict[str,list[Terminal]]]:
    """Fan non-display pads to 0.40/0.20 mm vias.

    Display-island nets are not fanned: MIPI/FPC/backlight stay as ratsnest.
    QFN pins use a 3-ring stagger so 0.40 mm vias clear a 0.35 mm pitch.
    """
    items: list[str]=[]
    terms: dict[str,list[Terminal]]={}
    used: list[tuple[float,float]]=[]
    min_sep = VIA_SIZE + 0.13

    def place_via(net: str, tx: float, ty: float, tag: str) -> tuple[float,float] | None:
        tx,ty=snap(tx),snap(ty)
        for ox,oy in used:
            if math.hypot(tx-ox,ty-oy)<min_sep:
                return None
        used.append((tx,ty))
        items.append(_via(tx,ty,net,net_ids,tag))
        terms.setdefault(net,[]).append(Terminal(net,tx,ty,VIA_SIZE,True))
        return tx,ty

    for dev in devs:
        for pad in dev.pads:
            net=dev.pins.get(pad.number,("",None))[1]
            if not net or net in DISPLAY_NETS:
                continue
            # Signal fanout on 0.35 mm QFN still shorts 0.40 mm vias. Only drop
            # vias that attach power pins to the pours; route signals in pcbnew.
            if dev.footprint in ("QFN40","QFN88","USB4105","MICROSD","LGA-12") and net not in PLANE_NETS:
                continue
            px,py=abs_pad(dev,pad)
            if pad.kind=="thru_hole":
                terms.setdefault(net,[]).append(Terminal(net,snap(px),snap(py),max(pad.sx,pad.sy)))
                continue
            if dev.footprint in ("FPC20","FPC45","USB4105"):
                continue
            lx,ly=pad.x,pad.y
            if dev.footprint in ("QFN40","QFN88") and pad.number in ("41","89"):
                continue
            if net in {"USB_DP","USB_DM"} and dev.footprint=="QFN88":
                vx,vy=(1.0 if net=="USB_DP" else -1.0),0.0
            elif abs(lx)>abs(ly):
                vx,vy=math.copysign(1,lx),0.0
            elif math.hypot(lx,ly)<.01:
                vx,vy=0.0,-1.0
            else:
                vx,vy=0.0,math.copysign(1,ly)
            a=math.radians(dev.rotation); ca,sa=math.cos(a),math.sin(a)
            rx,ry=vx*ca-vy*sa, vx*sa+vy*ca
            if dev.footprint in ("QFN40","QFN88") and pad.number.isdigit():
                ring=int(pad.number)%3
                distance=1.50+ring*0.95
            elif dev.footprint=="MICROSD" and pad.number.isdigit() and int(pad.number)<=9:
                vx,vy=0.0,1.0
                rx,ry=vx,vy
                distance=1.1
            elif dev.footprint=="USB4105":
                if net not in {"VBUS","GND"}:
                    continue
                vx,vy=0.0,-1.0
                rx,ry=vx,vy
                distance=1.6
            else:
                distance=0.85
            width=.20 if net in PLANE_NETS else .12
            placed=None
            for extra in (0.0,0.4,0.8,1.2):
                tx=px+rx*(distance+extra); ty=py+ry*(distance+extra)
                if math.hypot(px-tx,py-ty)>.05:
                    # probe occupancy before committing the stub
                    trial=True
                    ttx,tty=snap(tx),snap(ty)
                    for ox,oy in used:
                        if math.hypot(ttx-ox,tty-oy)<min_sep:
                            trial=False; break
                    if not trial:
                        continue
                    items.append(f'\t(segment (start {px:.4f} {py:.4f}) (end {ttx:.4f} {tty:.4f}) (width {width:.3f}) (layer "F.Cu") (net {net_ids[net]}) (uuid {q(uid(f"escape-{dev.ref}-{pad.number}"))}))')
                    placed=place_via(net,ttx,tty,f"escape-via-{dev.ref}-{pad.number}")
                    if placed:
                        break
            _=placed
    return items,terms


def autoroute(terminals: dict[str,list[Terminal]], net_ids: dict[str,int]) -> tuple[list[str],dict[str,float]]:
    """Deterministic two-layer maze router for the escaped low-speed nets.

    In1.Cu remains an uninterrupted ground reference. B.Cu and In2.Cu carry
    orthogonal/maze-routed signals; every layer change is a plated through via.
    """
    grid=.2; nx=int(58/grid)+1; ny=int(110/grid)+1
    layers=("B.Cu","In2.Cu")
    occ=[{} for _ in layers]  # cell -> set of occupying nets

    def mark(layer: int, ix: int, iy: int, net: str, radius_cells: float) -> None:
        rr=math.ceil(radius_cells)
        for dx in range(-rr,rr+1):
            for dy in range(-rr,rr+1):
                if dx*dx+dy*dy <= radius_cells*radius_cells+1e-9:
                    occ[layer].setdefault((ix+dx,iy+dy),set()).add(net)

    def mark_routed(layer: int, ix: int, iy: int, net: str, radius_cells: float) -> None:
        """Add routed copper while preserving pre-reserved foreign escapes."""
        rr=math.ceil(radius_cells)
        for dx in range(-rr,rr+1):
            for dy in range(-rr,rr+1):
                if dx*dx+dy*dy > radius_cells*radius_cells+1e-9: continue
                cell=(ix+dx,iy+dy); owners=occ[layer].get(cell)
                if owners and net not in owners: continue
                occ[layer].setdefault(cell,set()).add(net)

    # Escape vias occupy both routing layers. Do not pre-reserve long
    # outward corridors: those walls boxed later nets inside the QFN ring.
    for net,ts in terminals.items():
        for t in ts:
            ix=round(t.x/grid); iy=round(t.y/grid)
            radius=(t.radius/2+.10+.06)/grid
            for layer in range(2): mark(layer,ix,iy,net,radius)
    # Keep the high-speed groups leaving each endpoint toward the connector-to-
    # SoC corridor.  Without these one-cell guards a shortest-path search can
    # wrap one member around the back of an adjacent fine-pitch terminal.
    for net,ts in terminals.items():
        if not (net.startswith("DSI_") or net.startswith("USB_D")): continue
        ys=[round(t.y/grid) for t in ts]; ymin,ymax=min(ys),max(ys)
        for t in ts:
            ix=round(t.x/grid); iy=round(t.y/grid)
            outside=iy-2 if iy==ymin else (iy+2 if iy==ymax else None)
            if outside is not None:
                for layer in range(2): mark(layer,ix,outside,"#HS_GUARD",0.0)
    # Mechanical holes are hard obstacles.
    for x,y in ((3,3),(55,3),(3,107),(55,107)):
        for layer in range(2): mark(layer,round(x/grid),round(y/grid),"#HOLE",(1.2+.15+.06)/grid)
    # Leave the SoC-to-FPC corridor empty for a later OLED MIPI bundle.
    for ix in range(round(24/grid), round(36/grid)+1):
        for iy in range(round(40/grid), round(50/grid)+1):
            for layer in range(2): mark(layer,ix,iy,"#DISPLAY_KEEP",0.0)

    def free(state: tuple[int,int,int], net: str) -> bool:
        ix,iy,layer=state
        if ix<2 or iy<2 or ix>nx-3 or iy>ny-3: return False
        return all(owner==net for owner in occ[layer].get((ix,iy),()))

    def route_one(starts: set[tuple[int,int,int]], targets: set[tuple[int,int,int]], net: str) -> list[tuple[int,int,int]] | None:
        txs=[s[0] for s in targets]; tys=[s[1] for s in targets]
        bx0,bx1=min(txs),max(txs); by0,by1=min(tys),max(tys)
        def heuristic(s: tuple[int,int,int]) -> int:
            x,y,_=s
            return max(bx0-x,0,x-bx1)+max(by0-y,0,y-by1)
        queue=[]; score={}; came={}; serial=0
        for s in starts:
            score[s]=0; heapq.heappush(queue,(heuristic(s),0,serial,s)); serial+=1
        hit=None; expansions=0
        while queue and expansions<800000:
            _f,g,_s,cur=heapq.heappop(queue)
            if g!=score.get(cur): continue
            if cur in targets: hit=cur; break
            expansions+=1
            x,y,layer=cur
            candidates=[((x+1,y,layer),1),((x-1,y,layer),1),((x,y+1,layer),1),((x,y-1,layer),1),((x,y,1-layer),14)]
            for nxt,cost in candidates:
                if not free(nxt,net): continue
                if nxt[2]!=layer and not free((x,y,layer),net): continue
                ng=g+cost
                if ng<score.get(nxt,10**18):
                    score[nxt]=ng; came[nxt]=cur
                    heapq.heappush(queue,(ng+heuristic(nxt),ng,serial,nxt)); serial+=1
        if hit is None: return None
        path=[hit]
        while path[-1] not in starts: path.append(came[path[-1]])
        path.reverse(); return path

    skip=PLANE_NETS | DISPLAY_NETS
    work=[]
    for net,ts in terminals.items():
        unique={(round(t.x/grid),round(t.y/grid)) for t in ts if t.active}
        if net in skip or len(unique)<2: continue
        span=(max(x for x,_ in unique)-min(x for x,_ in unique))+(max(y for _,y in unique)-min(y for _,y in unique))
        work.append((net,unique,span))
    power_first={"1V8","CORE_0V93","DRAM_1V5","RTC_3V3","VSYS","VBAT","VBUS","SD_3V3"}
    sd_bus={"SD_D0","SD_D1","SD_D2","SD_D3","SD_CMD","SD_CLK","SD_DET"}
    nand_bus={"BOOT0","BOOT1"}
    display_ctrl={"LCD_TE","LCD_EN","LCD_RST"}
    pmic_bus={"PMIC_SCL","PMIC_SDA","PMIC_IRQ_N"}
    priority=lambda net: 0 if net=="LCD_RST" else (1 if net.startswith("USB_D") else (2 if net=="VBUS" else (3 if net=="VBAT" else (4 if net=="SD_3V3" else (5 if net=="SD_PWR_EN" else (6 if net in sd_bus else (7 if net.startswith("DSI_") else (8 if net in nand_bus else (9 if net=="1V8" else (10 if net=="CORE_0V93" else (11 if net in pmic_bus else (12 if net in display_ctrl else (13 if net in power_first else 14)))))))))))))
    work.sort(key=lambda item:(priority(item[0]),-item[2],-len(item[1]),item[0]))
    output=[]; lengths: dict[str,float]={}
    failed: list[str]=[]
    for net,points,_span in work:
        if net=="SD_3V3": root=min(points,key=lambda p:(p[1],p[0]))
        elif net in power_first: root=min(points,key=lambda p:(p[1],p[0]))
        elif net in sd_bus or net in nand_bus: root=min(points,key=lambda p:(p[1],p[0]))
        elif net.startswith("USB_D"): root=min(points,key=lambda p:(p[1],p[0]))
        else: root=min(points)
        tree={(root[0],root[1],0),(root[0],root[1],1)}
        remaining=set(points); remaining.remove(root)
        total=0.0; branch=0
        routed=True
        while remaining:
            point=min(remaining,key=lambda p:min(abs(p[0]-t[0])+abs(p[1]-t[1]) for t in tree))
            targets={(point[0],point[1],0),(point[0],point[1],1)}
            path=route_one(tree,targets,net)
            if path is None:
                failed.append(f"{net}@{point}")
                routed=False
                break
            branch+=1
            # Emit the uncompressed grid walk. KiCad coalesces visually; keeping
            # each step makes obstacle accounting and length audit deterministic.
            for idx in range(len(path)-1):
                a=path[idx]; b=path[idx+1]
                if a[2]!=b[2]:
                    x=a[0]*grid; y=a[1]*grid
                    output.append(_via(x,y,net,net_ids,f"route-via-{net}-{branch}-{idx}"))
                    for layer in range(2): mark_routed(layer,a[0],a[1],net,2.0)
                else:
                    x1=a[0]*grid; y1=a[1]*grid; x2=b[0]*grid; y2=b[1]*grid
                    width=.25 if net in {"VBUS","VBAT","VSYS","CORE_0V93","DRAM_1V5","1V8","RTC_3V3","LCD_3V3","SD_3V3","LEDA","LEDK"} else .12
                    output.append(f'\t(segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (width {width:.3f}) (layer {q(layers[a[2]])}) (net {net_ids[net]}) (uuid {q(uid(f"route-seg-{net}-{branch}-{idx}"))}))')
                    total+=grid
                tree.add(a); tree.add(b)
            for x,y,layer in path: mark_routed(layer,x,y,net,1.1)
            # A through via is present at every escape terminal.
            tree.add((point[0],point[1],0)); tree.add((point[0],point[1],1))
            remaining.remove(point)
        if routed:
            lengths[net]=total
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"unrouted_nets.txt").open("w") as f:
        f.write("# Non-display nets the maze did not finish. Display nets are frozen and omitted.\n")
        for item in failed:
            f.write(item+"\n")
        if not failed:
            f.write("# none\n")
    return output,lengths


def copper_zones(net_ids: dict[str,int]) -> list[str]:
    def zone(net: str, layer: str, priority: int, points: list[tuple[float,float]], suffix: str) -> str:
        pts=" ".join(f"(xy {x:g} {y:g})" for x,y in points)
        return f'''\t(zone (net {net_ids[net]}) (net_name {q(net)}) (layer {q(layer)}) (uuid {q(uid("zone-"+net+"-"+layer))}) (hatch edge 0.5) (priority {priority})
\t\t(connect_pads (clearance .10)) (min_thickness .12) (fill yes (thermal_gap .25) (thermal_bridge_width .25))
\t\t(polygon (pts {pts}))
\t)'''
    full=[(.5,.5),(57.5,.5),(57.5,109.5),(.5,109.5)]
    # A single concave polygon forms the SoC lobe, PMIC lobe and connecting neck.
    core=[(2,82),(15,82),(15,64),(21,64),(21,48),(38,48),(38,64),(25,64),(25,100),(2,100)]
    v1v8=[(12,46),(46,46),(46,76),(24,76),(24,100),(12,100)]
    dram=[(2,86),(10,86),(10,100),(2,100)]
    rtc=[(4,14),(36,14),(36,32),(6,32),(6,92),(20,92),(20,78),(4,78)]
    lcd3=[(14,36),(34,36),(34,44),(14,44)]
    return [
        zone("GND","In1.Cu",1,full,"plane"),
        zone("3V3","In2.Cu",1,full,"plane"),
        zone("CORE_0V93","In2.Cu",2,core,"pour"),
        zone("1V8","B.Cu",3,v1v8,"pour"),
        zone("DRAM_1V5","B.Cu",4,dram,"pour"),
        zone("RTC_3V3","B.Cu",3,rtc,"pour"),
        zone("LCD_3V3","B.Cu",4,lcd3,"pour"),
    ]


def manual_front_routes(net_ids: dict[str,int]) -> list[str]:
    """Top-layer routes that must pass outside the buried high-speed bundle."""
    paths={
        "LCD_RST":[(23.2,50.4),(11.0,50.4),(11.0,34.0),(33.8,34.0),(33.8,39.8)],
        "LCD_EN":[(23.2,51.6),(24.5,51.6),(24.5,48.8),(18.2,48.8),(18.2,41.4)],
        "LEDA":[(34.8,39.8),(34.8,36.0),(49.0,36.0)],
        "LEDK":[(34.2,39.8),(34.2,42.6),(44.0,42.6)],
        "LCD_3V3":[(16.0,40.0),(20.0,40.0),(27.0,40.0),(27.0,39.0)],
    }
    out=[]
    for net,points in paths.items():
        for idx,(a,b) in enumerate(zip(points,points[1:])):
            out.append(f'\t(segment (start {a[0]:.4f} {a[1]:.4f}) (end {b[0]:.4f} {b[1]:.4f}) (width .12) (layer "F.Cu") (net {net_ids[net]}) (uuid {q(uid(f"manual-{net}-{idx}"))}))')
    return out


def board(devs: list[Device]) -> str:
    raise RuntimeError("Legacy whole-board regeneration disabled. Preserve the current PCB.")
    nets=sorted({net for d in devs for _n,net in d.pins.values() if net})
    net_ids={n:i+1 for i,n in enumerate(nets)}
    out=['(kicad_pcb','\t(version 20241229)','\t(generator "sameat-evt1-r1")','\t(generator_version "r1")','\t(general (thickness 1.0) (legacy_teardrops no))','\t(paper "A4")','\t(layers (0 "F.Cu" signal) (2 "In1.Cu" power "GND plane") (4 "In2.Cu" power "3V3 plane") (6 "B.Cu" signal) (9 "F.Adhes" user "F.Adhesive") (11 "B.Adhes" user "B.Adhesive") (13 "F.Paste" user) (15 "B.Paste" user) (5 "F.SilkS" user "F.Silkscreen") (7 "B.SilkS" user "B.Silkscreen") (1 "F.Mask" user) (3 "B.Mask" user) (17 "Dwgs.User" user "User.Drawings") (19 "Cmts.User" user "User.Comments") (25 "Edge.Cuts" user) (27 "Margin" user) (31 "F.CrtYd" user) (29 "B.CrtYd" user) (35 "F.Fab" user) (33 "B.Fab" user))','\t(setup (pad_to_mask_clearance 0) (allow_soldermask_bridges_in_footprints no) (tenting front back))','\t(net 0 "")']
    out += [f'\t(net {i} {q(n)})' for n,i in net_ids.items()]
    out += [footprint_instance(d,net_ids) for d in devs]
    routes, _fanout_report = deterministic_fanout_and_routes(devs, net_ids)
    therm=[]
    for name,cx,cy,span in (("u2",30.0,56.0,2.4),("u1",18.0,85.0,1.6)):
        n=0
        for dx in (-span/2,0,span/2):
            for dy in (-span/2,0,span/2):
                n+=1
                therm.append(_via(cx+dx,cy+dy,"GND",net_ids,f"thermal-{name}-{n}"))
    out += therm+routes+copper_zones(net_ids)
    out += ['\t(gr_rect (start 22 38) (end 38 53) (stroke (width .15) (type dash)) (fill none) (layer "Dwgs.User") (uuid "'+uid('display-keepout')+'"))']
    out += ['\t(gr_text "DISPLAY ISLAND FROZEN\\n(MIPI / FPC / backlight)" (at 30 45) (layer "Dwgs.User") (uuid "'+uid('display-keepout-text')+'") (effects (font (size 0.8 0.8) (thickness .12))))']
    # Board-only mounting holes.
    for i,(x,y) in enumerate([(3,3),(55,3),(3,107),(55,107)],1):
        out += [f'\t(footprint "MountingHole_{i}" (layer "F.Cu") (at {x} {y}) (uuid {q(uid(f"mh{i}"))}) (property "Reference" {q(f"H{i}")} (at 0 -3 0) (layer "F.SilkS") (effects (font (size .8 .8)))) (property "Value" "M2" (at 0 3 0) (layer "F.Fab") (effects (font (size .8 .8)))) (attr board_only exclude_from_pos_files exclude_from_bom) (fp_circle (center 0 0) (end 2 0) (stroke (width .2) (type default)) (fill none) (layer "F.SilkS")) (pad "" np_thru_hole circle (at 0 0) (size 2.4 2.4) (drill 2.4) (layers "*.Cu" "*.Mask")))']
    out += [
        '\t(gr_rect (start 0 0) (end 58 110) (stroke (width .1) (type default)) (fill none) (layer "Edge.Cuts") (uuid "'+uid('edge')+'"))',
        '\t(gr_rect (start 4 15) (end 54 95) (stroke (width .15) (type dash)) (fill none) (layer "B.SilkS") (uuid "'+uid('battery-keepout')+'"))',
        '\t(gr_text "BATTERY KEEPOUT 50x80x6mm" (at 29 55 90) (layer "B.SilkS") (uuid "'+uid('battery-text')+'") (effects (font (size 1 1) (thickness .15))))',
        '\t(gr_text "Portable Display V1.0-EVT1\\nNOT PHYSICALLY VALIDATED" (at 29 103) (layer "B.SilkS") (uuid "'+uid('board-title')+'") (effects (font (size 1 1) (thickness .15)) (justify mirror)))',
        '\t(embedded_fonts no)',')']
    return "\n".join(out)+"\n"


def write_bom(devs: list[Device]) -> None:
    raise RuntimeError("Use export_metadata.py: placement must be taken from the actual PCB")


def main() -> None:
    """Explicit source regeneration only; never rewrites the routed PCB or docs."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-schematics", action="store_true", help="Explicitly regenerate the four sheets and local libraries from Device records")
    args = parser.parse_args()
    if os.environ.get("EVT1_REBUILD_BOARD"):
        parser.error("EVT1_REBUILD_BOARD is retired: routed PCB rebuilds are not a verification step")
    if not args.write_schematics:
        print("No files changed. Verify with: python3 tools/verify_evt1.py --static")
        print("To regenerate source sheets explicitly: --write-schematics")
        return
    devs=devices()
    root,sheets=root_schematic()
    (ROOT/"portable_display_epass.kicad_sch").write_text(root,encoding="utf-8")
    mapping={"power":"01_power.kicad_sch","soc":"02_soc_v851s.kicad_sch","sensors":"03_sensors.kicad_sch","interfaces":"04_interfaces.kicad_sch"}
    for name,file in mapping.items():
        (ROOT/file).write_text(schematic_for_sheet(name,devs,uid("root-schematic"),sheets[name]),encoding="utf-8")
    library="(kicad_symbol_lib (version 20241209) (generator sameat)\n"+"\n".join(symbol_library_entry(d).replace('(symbol "Sameat:', '(symbol "') for d in devs)+"\n"+supply_source_symbol().replace('(symbol "Sameat:', '(symbol "')+"\n)\n"
    (ROOT/"sameat.kicad_sym").write_text(library,encoding="utf-8")
    write_local_footprints(devs)
    print(f"Regenerated source sheets for {len(devs)} devices; PCB and documentation preserved")

if __name__=="__main__":
    main()
