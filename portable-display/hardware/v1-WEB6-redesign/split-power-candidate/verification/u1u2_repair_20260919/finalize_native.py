from last_signals import *
import subprocess,collections
shutil.copy2(P,W/'33_before_cleanup.kicad_pcb')
b=rb.load(P);seen={};out=[]
for n in b:
 if isinstance(n,list) and n and n[0] in ('segment','via'):
  key=str(val(n,'uuid'))
  if key in seen:
   assert dumps(n)==dumps(seen[key]);print('remove duplicate',key,flush=True);continue
  seen[key]=n
 out.append(n)
save(out)
log=[]
for turn in range(20):
 result=subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc','--refill-zones','--save-board','--format','json','-o',str(W/'drc_final.json'),str(P)],check=True,capture_output=True,text=True)
 j=json.loads((W/'drc_final.json').read_text());types=dict(collections.Counter(v['type'] for v in j['violations']));print('Native pass',turn,types,'unconnected',len(j['unconnected_items']),flush=True);log.append({'round':turn,'types':types,'unconnected':len(j['unconnected_items'])})
 if not j['violations']:break
 if any(v['type'] not in ('track_dangling','via_dangling','track_not_centered_on_via') for v in j['violations']):break
 old=P.read_bytes()
 subprocess.run([sys.executable,str(R/'tools/clean_routing_remnants.py'),str(P),str(W/'drc_final.json'),'--report',str(W/f'cleanup_{turn}.json')],check=True)
 prune();prune(['GND'])
 if P.read_bytes()==old:break
(W/'cleanup_passes.json').write_text(json.dumps(log,indent=2)+'\n')
