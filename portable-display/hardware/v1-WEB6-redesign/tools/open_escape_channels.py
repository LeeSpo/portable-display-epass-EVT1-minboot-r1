#!/usr/bin/env python3
"""Specific coordinated local placement/routing edit for the 2026-09-10 candidate."""
import pcbnew,sys,json
from pathlib import Path
p=sys.argv[1];b=pcbnew.LoadBoard(p);report={'moves':[],'removed':[],'via_moves':[]}
def v(x,y):return pcbnew.VECTOR2I(pcbnew.FromMM(x),pcbnew.FromMM(y))
def pos(p):return [pcbnew.ToMM(p.x),pcbnew.ToMM(p.y)]
def move_via(key,x,y):
 t=next((t for t in b.GetTracks() if t.m_Uuid.AsString()==key),None)
 if t is None:return
 old=pcbnew.VECTOR2I(t.GetPosition());new=v(x,y)
 for s in b.GetTracks():
  if isinstance(s,pcbnew.PCB_VIA) or s.GetNetCode()!=t.GetNetCode():continue
  if s.GetStart()==old:s.SetStart(new)
  if s.GetEnd()==old:s.SetEnd(new)
 report['via_moves'].append([t.GetNetname(),pos(old),[x,y]]);t.SetPosition(new)
move_via('ba80d462-de97-5511-803e-0ca0e2d86d50',21.8,28)
move_via('013b0fe5-4a50-5013-8245-9881b8e18b82',22,29)
for ref,x,y,angle in [('C14',25.35,31.275,0),('C16',17.625,34.75,0)]:
 f=b.FindFootprintByReference(ref);before={p.GetNumber():pcbnew.VECTOR2I(p.GetPosition()) for p in f.Pads()}
 report['moves'].append({'ref':ref,'from':pos(f.GetPosition())+[f.GetOrientationDegrees()],'to':[x,y,angle]})
 f.SetOrientationDegrees(angle);f.SetPosition(v(x,y))
 for pad in f.Pads():
  old=before[pad.GetNumber()];new=pad.GetPosition()
  for t in b.GetTracks():
   if isinstance(t,pcbnew.PCB_VIA) or t.GetNetCode()!=pad.GetNetCode():continue
   if t.GetStart()==old:t.SetStart(new)
   if t.GetEnd()==old:t.SetEnd(new)
for t in list(b.GetTracks()):
 net=t.GetNetname();key=t.m_Uuid.AsString();remove=False
 if net in ['SD_D0','SD_D2','LCD_EN','LCD_TE','LCD_RST']:remove=True
 if net=='CORE_0V93' and not isinstance(t,pcbnew.PCB_VIA) and t.GetLayer()==pcbnew.B_Cu:remove=True
 if key in ['3435af7d-5015-5fe4-bf72-d2e59557e29f','6498e89e-c582-5d6c-8d39-96cf9b5221e0']:remove=True
 if isinstance(t,pcbnew.PCB_VIA) and net=='GND' and abs(pcbnew.ToMM(t.GetPosition().x)-25.2804)<.001 and abs(pcbnew.ToMM(t.GetPosition().y)-31.891)<.001:remove=True
 if net=='USB_DP' and not isinstance(t,pcbnew.PCB_VIA):
  a,c=pos(t.GetStart()),pos(t.GetEnd())
  if max(a[1],c[1])<33.31:remove=True
  elif a==[9.5,38.6] and c==[9.5,33.3]:t.SetEnd(v(9.5,34.1))
  elif c==[9.5,38.6] and a==[9.5,33.3]:t.SetStart(v(9.5,34.1))
 if net=='SD_CLK' and not isinstance(t,pcbnew.PCB_VIA):
  for getter,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
   x,y=pos(getter())
   if abs(x-26.3)<.01 and 30.3<y<33.5:setter(v(26.65,y))
 if remove:report['removed'].append({'uuid':key,'net':net});b.Remove(t)
pcbnew.SaveBoard(p,b);Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['moves']))
