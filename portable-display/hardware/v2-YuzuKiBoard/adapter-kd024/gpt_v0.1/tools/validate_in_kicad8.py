#!/usr/bin/env python3
"""Run native KiCad 8 checks on an isolated copy. NEVER grants fabrication release.
Use KiCad's Python environment (for pcbnew), or system Python with that module.
"""
from pathlib import Path
import json,shutil,subprocess,sys,re
root=Path(__file__).resolve().parents[1];out=root/'reports/native_kicad8';out.mkdir(exist_ok=True)
result={'fabrication_released':False,'native_erc':'NOT_RUN','native_drc':'NOT_RUN','zone_refill':'NOT_RUN','note':'Review evidence only. DSI still unrouted; no automatic release.'}
def save():
 (out/'native_attempt.json').write_text(json.dumps(result,indent=2))
def run(args,name):
 p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
 (out/(name+'.log')).write_text(p.stdout);return p
cli=shutil.which('kicad-cli')
if not cli:
 result['reason']='kicad-cli not found on PATH; native checks were NOT run.';save();print(result['reason']);sys.exit(2)
v=run([cli,'--version'],'version');result['version']=v.stdout.strip()
if not re.match(r'^8\.',v.stdout.strip()):
 result['reason']='This validation entry point requires KiCad 8.x. Do not imply a different major version was validated.';save();print(result['reason']);sys.exit(2)
copy=out/'candidate_kicad';shutil.copytree(root/'kicad',copy,dirs_exist_ok=True)
board=copy/'adapter_v0.1.kicad_pcb';sch=copy/'adapter_v0.1.kicad_sch'
code='import pcbnew,sys; b=pcbnew.LoadBoard(sys.argv[1]); pcbnew.ZONE_FILLER(b).Fill(b.Zones()); pcbnew.SaveBoard(sys.argv[1],b)'
f=run([sys.executable,'-c',code,str(board)],'zone_refill')
result['zone_refill']='COMPLETED' if f.returncode==0 else 'FAILED_CHECK_LOG'
e=run([cli,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(out/'erc.json'),str(sch)],'erc')
d=run([cli,'pcb','drc','--format','json','--all-track-errors','--schematic-parity','--severity-all','--exit-code-violations','-o',str(out/'drc.json'),str(board)],'drc')
result['native_erc']={'return_code':e.returncode,'report':'erc.json'};result['native_drc']={'return_code':d.returncode,'report':'drc.json'}
result['note']='Inspect actual JSON and logs. Zero exit alone does not approve FFC, bias, impedance, procurement or hardware behavior.'
save();print(json.dumps(result,indent=2));sys.exit(0 if f.returncode==e.returncode==d.returncode==0 else 1)
