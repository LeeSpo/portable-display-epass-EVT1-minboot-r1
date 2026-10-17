from repair import *
import hashlib,collections

def audit(board=P,drc=W/'drc_final.json'):
 b=rb.load(board);o=rb.load(W/'original.kicad_pcb');r=RepairRouter(b);dr=json.loads(Path(drc).read_text())
 def refs(tree):return {str(next(p[2] for p in children(f,'property') if p[1]=='Reference')):f for f in children(tree,'footprint')}
 old,new=refs(o),refs(b)
 def mapping(fps):return {n:{str(p[1]):str(values(p,'net')[-1]) if values(p,'net') else '' for p in children(f,'pad') if str(p[1])} for n,f in fps.items()}
 placement={n:[values(old[n],'at'),values(f,'at')] for n,f in new.items() if values(old[n],'at')!=values(f,'at') or val(old[n],'layer')!=val(f,'layer')}
 critical={}
 for net in sorted(CRITICAL|{'EL_SWP','EL_SWN'}):
  its=[i for i in r.items if i.net==net];ts=[i for i in its if i.kind=='track'];critical[net]={'layers':sorted(set(l for i in ts for l in i.layers)),'vias':sum(i.kind=='via' for i in its),'total_copper_length_mm':round(sum(math.dist(*i.pos) for i in ts),4)}
 vips=[]
 for i in r.items:
  if i.kind!='via':continue
  for p in r.items:
   if p.kind=='pad' and p.node[2]=='smd' and p.layers and i.hole.intersects(p.geom):vips.append({'via_uuid':i.label,'net':i.net,'at_mm':i.pos,'pad':p.label,'pad_net':p.net})
 ground_power={n:len(r.groups(n)) for n in ['GND','VSYS','3V3','1V8','CORE_0V93','DRAM_1V5','VBAT']}
 footprint={}
 for ref in ['U1','U2']:
  f=new[ref];pads=children(f,'pad');ep=next(p for p in pads if str(p[1])==('41' if ref=='U1' else '89'));paste=[p for p in pads if str(p[1])==''];area=sum(float(values(p,'size')[0])*float(values(p,'size')[1])-(4-math.pi)*(min(map(float,values(p,'size')))*float(val(p,'roundrect_rratio',0)))**2 for p in paste)
  footprint[ref]={'ep_size_mm':list(map(float,values(ep,'size'))),'peripheral_size_mm':list(map(float,values(next(p for p in pads if str(p[1])=='1'),'size'))),'paste_apertures':len(paste),'paste_coverage_percent':round(100*area/math.prod(map(float,values(ep,'size'))),2),'land_basis':'engineering design derived from manufacturer package drawings; assembly qualification pending'}
 assert footprint['U1']['ep_size_mm']==[3.4,3.4] and footprint['U2']['ep_size_mm']==[6.5,6.5]
 assert sorted(footprint['U1']['peripheral_size_mm'])==[.2,.7] and sorted(footprint['U2']['peripheral_size_mm'])==[.18,.7]
 report={'board_sha256':hashlib.sha256(Path(board).read_bytes()).hexdigest(),'original_board_sha256':hashlib.sha256((W/'original.kicad_pcb').read_bytes()).hexdigest(),'footprints':len(new),'all_front':all(str(val(f,'layer'))=='F.Cu' for f in new.values()),'numbered_pad_net_map_unchanged':mapping(old)==mapping(new),'placement_changes_this_repair':placement,'native_drc':{'unconnected':len(dr['unconnected_items']),'violations':dict(collections.Counter(v['type'] for v in dr['violations']))},'critical_nets':critical,'ground_power_pad_groups':ground_power,'trace_count':sum(i.kind=='track' for i in r.items),'via_count':sum(i.kind=='via' for i in r.items),'via_in_pad':vips,'u1_u2':footprint,'in1_signal_tracks':sum(i.kind=='track' and 'In1.Cu' in i.layers for i in r.items),'in1_ground_polygons':sum(i.net=='GND' and 'In1.Cu' in i.layers for i in r.zones),'fabrication_released':False}
 report['project_rules_unchanged']=P.with_suffix('.kicad_pro').read_bytes()==(C/'ak_display_38x64_SPLIT_POWER_CANDIDATE.kicad_pro').read_bytes()
 report['in2_track_length_mm']=round(sum(math.dist(*i.pos) for i in r.items if i.kind=='track' and 'In2.Cu' in i.layers),4)
 report['in2_track_length_by_net_mm']={n:round(sum(math.dist(*i.pos) for i in r.items if i.kind=='track' and 'In2.Cu' in i.layers and i.net==n),4) for n in sorted(set(i.net for i in r.items if i.kind=='track' and 'In2.Cu' in i.layers))}
 report['in2_original_track_length_mm']=round(sum(math.dist(*i.pos) for i in rb.board_items(o) if i.kind=='track' and 'In2.Cu' in i.layers),4)
 assert report['project_rules_unchanged']
 (W/'final_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['via_in_pad','critical_nets']},indent=2))
 assert report['footprints']==119 and report['all_front'] and report['numbered_pad_net_map_unchanged']
 assert set(placement)=={'C38'}
 assert abs(float(placement['C38'][1][1])-float(placement['C38'][0][1])-.4)<1e-6
 assert placement['C38'][0][0]==placement['C38'][1][0] and placement['C38'][0][2:]==placement['C38'][1][2:]
 assert not dr['unconnected_items'] and not dr['violations']
 assert all(v==1 for v in ground_power.values())
 assert all(v['layers']==['F.Cu'] and v['vias']==0 for v in critical.values())
 assert report['in1_signal_tracks']==0 and report['in1_ground_polygons']==1
 return report
if __name__=='__main__':audit()
