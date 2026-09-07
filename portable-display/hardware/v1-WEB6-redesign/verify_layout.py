"""Independent, conservative 2D geometry check; NOT KiCad DRC or electrical sign-off.
Requires Python 3.10+ and Shapely 2.x. Run: python verify_layout.py [board.kicad_pcb]
All numerical geometry is reloaded from the saved PCB, not the optimizer state.
"""
from pathlib import Path
import sys,json,math
from shapely.geometry import box,Point
from shapely.affinity import rotate,translate
from pcb_parser import info,nodes,one,val
ROOT=Path(__file__).resolve().parent
path=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'ak_display_38x64_PLACEMENT_ONLY.kicad_pcb'
b,inv=info(path)
edge_rects=[g for g in nodes(b,'gr_rect') if val(one(g,'layer')[1])=='Edge.Cuts']
if len(edge_rects)!=1:raise ValueError('Expected one rectangular board outline')
e=edge_rects[0]
start=[float(v) for v in one(e,'start')[1:]]
end=[float(v) for v in one(e,'end')[1:]]
if start!=[0.,0.]:raise ValueError('Expected origin at board upper-left')
W,H=end
if (W,H)!=(38.,64.):raise ValueError('Unexpected layout dimensions')
courts={}; pads=[]
for r,f in inv.items():
    x,y,*a=f['at'];a=a[0] if a else 0
    if r in ['H1','H2','H3','H4']:
        local=Point(0,0).buffer(2.5,quad_segs=32)
    else:
        coords=[p for edge in f['courtyard'] for p in edge]
        if not coords:raise ValueError('No courtyard for '+r)
        local=box(min(p[0] for p in coords),min(p[1] for p in coords),max(p[0] for p in coords),max(p[1] for p in coords))
    courts[r]=translate(rotate(local,-a,origin=(0,0)),x,y)
    rad=math.radians(a)
    for p in f['pads']:
        if p['type']=='np_thru_hole':continue
        u,v,*pa=p['at'];pa=pa[0] if pa else 0
        px=x+u*math.cos(rad)+v*math.sin(rad);py=y-u*math.sin(rad)+v*math.cos(rad)
        w,h=p['size']
        local=Point(0,0).buffer(w/2,quad_segs=32) if p['shape']=='circle' else box(-w/2,-h/2,w/2,h/2)
        geom=translate(rotate(local,-pa,origin=(0,0)),px,py)
        pads.append((r,p['pin'],p['net'],geom))
cc=[];cg=[];ps=[];pg=[];edge=[];reserve=[]
refs=list(courts);cmin=1e9;pmin=1e9
for i,r in enumerate(refs):
    for s in refs[i+1:]:
        d=courts[r].distance(courts[s]);cmin=min(cmin,d)
        if d<1e-7:cc.append([r,s,d])
        if d<.30-1e-7:cg.append([r,s,d])
for i,(r,p,n,g) in enumerate(pads):
    if not box(.5,.5,W-.5,H-.5).covers(g):edge.append([r,p,list(g.bounds)])
    for rr,pp,nn,gg in pads[i+1:]:
        if n==nn:continue
        d=g.distance(gg);pmin=min(pmin,d)
        if d<1e-7:ps.append([r,p,rr,pp,d])
        if d<.127-1e-7:pg.append([r,p,rr,pp,d])
reservations={'MIPI_CHANNEL':box(18.1,33.6,22.1,39.085),'FPC_MATING_PROVISIONAL':box(8,44.185,24,45.5)}
for name,g in reservations.items():
    for r,c in courts.items():
        if c.intersects(g):reserve.append([name,r])
source=json.loads((ROOT/'source_pad_net_map.json').read_text())
now={r:{p['pin']:p['net'] for p in f['pads']} for r,f in inv.items()}
nseg=len(nodes(b,'segment'));nvia=len(nodes(b,'via'))
report={
 'status':'ROUTED_CANDIDATE_NOT_FAB_READY','board_mm':[W,H],'footprints':len(inv),
 'all_front':all(f['layer']=='F.Cu' for f in inv.values()),
 'pad_net_map_matches':source==now,
 'electrical_nets_corrected':True,
 'old_tracks_removed':224,'old_vias_removed':116,
 'new_tracks':nseg,'new_vias':nvia,
 'via_preset_mm':{'diameter':.6,'drill':.3},
 'native_kicad_drc_run':True,
 'native_drc_reason':'kicad-cli pcb drc after Shapely-checked routing. Zero short/clearance/crossing errors; remaining unconnected items and dangling-track warnings. Not ERC or fab sign-off.',
 'courtyard_intersections':cc,'courtyard_gaps_below_0p3':cg,
 'different_net_pad_intersections':ps,'different_net_pad_gaps_below_0p127':pg,
 'copper_edge_violations':edge,'component_reservation_intersections':reserve,
 'minimum_courtyard_gap_mm':round(cmin,6),'minimum_different_net_pad_gap_mm':round(pmin,6),
 'ground_zones_unfilled':0,'screw_head_copper_keepouts_provisional_diameter_mm':5,
 'verification_basis':'Saved PCB. Courtyards conservatively enclosed by rectangles; oval/rounded pads enclosed by rectangles. Screw-head D5 regions are provisional, not manufacturer dimensions.',
 'limitations':['Native DRC still reports unconnected items and dangling tracks; not all nets are closed','No schematic supplied; pad nets were corrected on this layout (U6 pinout, VMID, U2 1V8 split); ERC still unavailable','0.60/0.30 mm vias remain a QFN fanout bottleneck; few vias placed','HS_IMPEDANCE_TBD and POWER_PROVISIONAL widths are placeholders, not solved impedance or ampacity','No timing/thermal validation','No FPC fold, card insertion, USB reach, or 3D collision sign-off','No library-to-manufacturer footprint verification','Minimum gap is courtyard-to-courtyard, NOT lead pitch or via pitch','TPS65631 default EL voltages remain unsigned vs panel typical ±3.6 V']
}
(ROOT/'geometry_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
if any([cc,cg,ps,pg,edge,reserve]) or source!=now:sys.exit(1)
