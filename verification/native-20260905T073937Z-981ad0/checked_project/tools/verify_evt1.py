#!/usr/bin/env python3
"""Read-only verification. Native mode is default and fails if KiCad is absent.

Every native run uses a fresh isolated snapshot, refills zones, exports netlist,
executes ERC/DRC with schematic parity, and validates all reports. No fabrication
files are exported here. A --release check additionally requires all signoffs
and zero display exceptions; passing still does not assert physical validation.
"""
from __future__ import annotations
import argparse,datetime,hashlib,json,os,re,shutil,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')

def run_cmd(cmd,cwd,logs,name):
    r=subprocess.run([str(x) for x in cmd],cwd=cwd,capture_output=True,text=True,timeout=600,env={**os.environ,'LC_ALL':'C','KIPRJMOD':str(cwd)})
    (logs/(name+'.log')).write_text('$ '+' '.join(map(str,cmd))+'\n'+r.stdout+'\n'+r.stderr)
    if r.returncode!=0:raise RuntimeError(f'{name} failed with exit code {r.returncode}; see {name}.log')
    return r.stdout

def validate_signoffs(root):
    obj=json.loads((root/'design/release_gates.json').read_text())
    expected={'display','pmic_variant','pinouts_footprints','power_thermal_battery','stackup_si','full_routing','native_validation','bringup_firmware'}
    gates=obj.get('gates',[]);ids=[g.get('id') for g in gates]
    if len(ids)!=len(set(ids)) or set(ids)!=expected:return ['Release gate list missing, duplicated or unexpected']
    return [g['id']+': unsigned or missing evidence' for g in gates if g.get('status')!='approved' or not g.get('reviewer') or not g.get('evidence')]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--static',action='store_true');p.add_argument('--release',action='store_true');p.add_argument('--kicad-cli');p.add_argument('--kicad-python',help='Python executable with pcbnew (needed for zone refill on KiCad 9)');a=p.parse_args()
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
    out=ROOT/'verification'/('static-'+stamp if a.static else 'native-'+stamp);out.mkdir(parents=True)
    status={'mode':'STATIC_ONLY' if a.static else 'NATIVE','native_kicad_executed':False,'fabrication_released':False,'verification_passed':False,'problems':[]}
    try:
        if a.static and a.release:raise ValueError('Static-only mode can never perform a release check')
        from static_verify import snapshot,run as static_run
        before=snapshot(ROOT);status['source_sha256']=before
        structural=static_run(ROOT);write_json(out/'static_report.json',structural)
        if not structural['static_checks_passed']:raise RuntimeError('Static source/geometry checks failed; see static_report.json')
        if a.static:
            status['verification_passed']=True;status['scope']='Only the enumerated static checks; not electrical or fabrication approval'
        else:
            cli=a.kicad_cli or shutil.which('kicad-cli')
            if not cli:raise RuntimeError('kicad-cli is unavailable; native ERC/DRC were NOT executed')
            ver=run_cmd([cli,'version'],ROOT,out,'version').strip();status['kicad_version']=ver
            m=re.search(r'(\d+)\.',ver)
            if not m or int(m.group(1)) not in {9,10}:raise RuntimeError('Native workflow is written for KiCad 9/10; review newer versions before enabling')
            stage=out/'checked_project';stage.mkdir()
            for rel in before:
                src=ROOT/rel;dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
            board=stage/'portable_display_epass.kicad_pcb';sch=stage/'portable_display_epass.kicad_sch'
            helptext=run_cmd([cli,'pcb','drc','--help'],stage,out,'drc_help')
            # KiCad 10 supports native refill. For 9, use its own Python zone filler.
            flags=[]
            if '--refill-zones' in helptext and '--save-board' in helptext:flags=['--refill-zones','--save-board']
            else:
                py=a.kicad_python or sys.executable
                run_cmd([py,stage/'tools/refill_zones.py',board],stage,out,'refill_zones')
            run_cmd([cli,'sch','export','netlist','--format','kicadxml','--output',out/'netlist.xml',sch],stage,out,'netlist')
            run_cmd([cli,'sch','erc','--format','json','--severity-all','--output',out/'erc.json',sch],stage,out,'erc')
            run_cmd([cli,'pcb','drc','--format','json','--severity-all','--schematic-parity','--all-track-errors',*flags,'--output',out/'drc.json',board],stage,out,'drc')
            status['native_kicad_executed']=True
            from export_metadata import pin_csv
            from check_minboot import check_netlist,check_reports
            pin_csv(ROOT,out/'net_pin_report.csv')
            erc=json.loads((out/'erc.json').read_text());drc=json.loads((out/'drc.json').read_text())
            problems=check_netlist(out/'netlist.xml',out/'net_pin_report.csv')+check_reports(erc,drc,allow_display=not a.release)
            status['native_report_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (out/'netlist.xml',out/'erc.json',out/'drc.json')}
            status['checked_filled_board_sha256']=hashlib.sha256(board.read_bytes()).hexdigest()
            status['scope']='full board and release gates' if a.release else 'non-display; explicit display unconnected exceptions only'
            if a.release:problems+=validate_signoffs(ROOT)
            status['problems']=problems;status['verification_passed']=not problems
        if snapshot(ROOT)!=before:raise RuntimeError('Source files changed during verification; results invalidated')
    except Exception as e:
        status['verification_passed']=False;status['problems'].append(f'{type(e).__name__}: {e}')
    write_json(out/'status.json',status);write_json(ROOT/'verification/latest_attempt.json',{'run':out.name,**{k:status[k] for k in ('mode','native_kicad_executed','fabrication_released','verification_passed','problems')}})
    print(json.dumps({k:v for k,v in status.items() if k!='source_sha256'},indent=2));print('Report:',out/'status.json')
    raise SystemExit(0 if status['verification_passed'] else 2)
if __name__=='__main__':main()
