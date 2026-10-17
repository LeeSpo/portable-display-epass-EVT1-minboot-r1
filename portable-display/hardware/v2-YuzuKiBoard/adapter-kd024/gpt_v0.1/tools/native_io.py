"""Small, explicit KiCad S-expression reader, not a KiCad native validator."""
from __future__ import annotations
import re,json,math,pathlib
from geometry import *
class Atom(str):pass
def parse(text):
 toks=re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()]+',text)
 stack=[];root=None
 for t in toks:
  if t=='(':
   a=[]
   if stack:stack[-1].append(a)
   stack.append(a)
  elif t==')':
   if not stack:raise ValueError('Unbalanced close')
   a=stack.pop()
   if not stack:
    if root is not None:raise ValueError('Multiple roots')
    root=a
  else:
   if not stack:raise ValueError('Atom outside root')
   stack[-1].append(json.loads(t) if t.startswith('"') else Atom(t))
 if stack:raise ValueError('Unbalanced open')
 return root

def dump(x,level=0):
 if isinstance(x,list):
  if level==0:return '('+'\n'.join(dump(y,level+1) for y in x)+')\n'
  return '('+' '.join(dump(y,level+1) for y in x)+')'
 if isinstance(x,Atom):return str(x)
 if isinstance(x,(int,float)):return f'{x:.6f}'.rstrip('0').rstrip('.') if isinstance(x,float) else str(x)
 return json.dumps(x,ensure_ascii=False)
def children(node,key):return [x for x in node if isinstance(x,list) and x and x[0]==key]
def child(node,key,default=None):
 z=children(node,key);return z[0] if z else default
def floats(n):return list(map(float,n))
def read_pcb(path=None):
 path=path or ROOT/'kicad/adapter_v0.1.kicad_pcb';tree=parse(path.read_text());assert tree[0]=='kicad_pcb'
 out={'tree':tree,'parts':[],'pads':[],'tracks':[],'vias':[],'silk':[],'edge':[],'zones':[],'netnames':{},'source':str(path)}
 for nn in children(tree,'net'):out['netnames'][int(nn[1])]=nn[2]
 for fp in children(tree,'footprint'):
  at=child(fp,'at');x,y=float(at[1]),float(at[2]);ang=float(at[3]) if len(at)>3 else 0
  ref=next(x[2] for x in children(fp,'fp_text') if x[1]=='reference');val=next(x[2] for x in children(fp,'fp_text') if x[1]=='value')
  prop={x[1]:x[2] for x in children(fp,'property')};attr=child(fp,'attr',[])[1:]
  part={'ref':ref,'value':val,'footprint':fp[1],'x':x,'y':y,'angle':ang,'props':prop,'dnp':'dnp' in attr,'feature':'exclude_from_bom' in attr,'node':fp};out['parts'].append(part)
  for pa in children(fp,'pad'):
   at=child(pa,'at');px,py=floats(at[1:3]);xx,yy=trans(part,px,py);sz=child(pa,'size');ly=child(pa,'layers')[1:];nt=child(pa,'net');dr=child(pa,'drill');aa=float(at[3]) if len(at)>3 else 0
   out['pads'].append({'ref':ref,'num':pa[1],'kind':pa[2],'shape':pa[3],'x':xx,'y':yy,'w':float(sz[1]),'h':float(sz[2]),'angle':aa,'layers':list(ly),'drill':float(dr[1]) if dr else None,'net':nt[2] if nt else ''})
 for t in children(tree,'segment'):
  out['tracks'].append({'a':floats(child(t,'start')[1:]),'b':floats(child(t,'end')[1:]),'width':float(child(t,'width')[1]),'layer':child(t,'layer')[1],'net':out['netnames'][int(child(t,'net')[1])]})
 for v in children(tree,'via'):out['vias'].append({'x':float(child(v,'at')[1]),'y':float(child(v,'at')[2]),'size':float(child(v,'size')[1]),'drill':float(child(v,'drill')[1]),'net':out['netnames'][int(child(v,'net')[1])]})
 for z in children(tree,'zone'):
  if child(z,'keepout'):continue
  pts=child(child(z,'polygon'),'pts')[1:];p=Polygon([floats(v[1:]) for v in pts]);out['zones'].append({'layer':child(z,'layer')[1],'net':child(z,'net_name')[1],'shape':p,'node':z})
 for g in children(tree,'gr_line'):
  layer=child(g,'layer')[1];z={'a':floats(child(g,'start')[1:]),'b':floats(child(g,'end')[1:]),'width':float(child(child(g,'stroke'),'width')[1])}
  if layer=='Edge.Cuts':out['edge'].append(z)
  elif layer=='F.SilkS':out['silk'].append(dict(z,kind='line'))
 for g in children(tree,'gr_circle'):
  if child(g,'layer')[1]!='F.SilkS':continue
  c=floats(child(g,'center')[1:]);e=floats(child(g,'end')[1:]);r=math.dist(c,e);out['silk'].append({'kind':'circle','c':c,'r':r,'width':float(child(child(g,'stroke'),'width')[1]),'fill':child(g,'fill')[1]})
 for g in children(tree,'gr_text'):
  if child(g,'layer')[1]=='F.SilkS':out['silk'].append({'kind':'text','text':g[1],'at':floats(child(g,'at')[1:3]),'size':float(child(child(child(g,'effects'),'font'),'size')[1])})
 return out
