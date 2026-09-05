#!/usr/bin/env python3
"""Remove native-identified redundant copper; revalidation is mandatory."""
import argparse,json
from pathlib import Path
from kicad_sexpr import *

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('board',type=Path);p.add_argument('report',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 b=load(a.board);d=json.loads(a.report.read_text());remove={}
 for v in d['violations']:
  if v['type'] in ('via_dangling','track_dangling'):
   for i in v['items']:remove[i['uuid']]=v['type']
 removed=[]
 for node in list(b):
  if not isinstance(node,list):continue
  uid=str(val(node,'uuid',''))
  if uid in remove and node[0] in ('via','segment'):
   b.remove(node);removed.append({'uuid':uid,'reason':remove[uid]})
 # The small R4 pull-up pour has only one usable spoke. Replace it with a
 # routed connection in the closure pass; leave the global thermal rule intact.
 for z in list(children(b,'zone')):
  if str(val(z,'uuid'))=='801ea914-1242-5d3b-968c-b3afa44e4ef7':
   b.remove(z);removed.append({'uuid':str(val(z,'uuid')),'reason':'replace isolated pull-up pour with track'})
 for t in children(b,'gr_text'):
  if 'ENGINEERING ONLY' in str(t[1]):
   setval(t,'at',29,105)
   font=child(child(t,'effects',[]),'font',[]);setval(font,'size',.8,.8);setval(font,'thickness',.12)
 for z in children(b,'zone'):z[:]=[x for x in z if not isinstance(x,list) or x[0] not in ('filled_polygon','fill_segments')]
 dump(b,a.output);print(json.dumps(removed,indent=2))
if __name__=='__main__':main()
