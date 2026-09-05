"""Small lossless-atom S-expression parser for KiCad files (no evaluation)."""
import json,re
from pathlib import Path
class Q(str): pass
TOKEN = re.compile(r'\s+|;[^\n]*(?:\n|$)|\(|\)|"(?:\\.|[^"\\])*"|[^\s();]+')
def loads(text):
    stack=[]; roots=[]; pos=0
    for m in TOKEN.finditer(text):
        if m.start()!=pos: raise ValueError(f'Invalid token at {pos}')
        pos=m.end();t=m.group()
        if t.isspace() or t.startswith(';'):continue
        if t=='(':
            a=[]
            if stack:stack[-1].append(a)
            else:roots.append(a)
            stack.append(a)
        elif t==')':
            if not stack:raise ValueError('Unexpected closing parenthesis')
            stack.pop()
        else:
            if not stack:raise ValueError('Atom outside expression')
            stack[-1].append(Q(json.loads(t)) if t.startswith('"') else t)
    if stack or pos!=len(text) or len(roots)!=1:raise ValueError('Unbalanced or multiple roots')
    return roots[0]
def load(p):return loads(Path(p).read_text(encoding='utf-8'))
def children(a,k):return [x for x in a if isinstance(x,list) and x and x[0]==k]
def child(a,k,default=None):
    z=children(a,k);return z[0] if z else default
def val(a,k,default=None):
    z=child(a,k);return z[1] if z is not None and len(z)>1 else default
def values(a,k,default=()):
    z=child(a,k);return z[1:] if z is not None else default
def setval(a,k,*v):
    z=child(a,k)
    if z is None:a.append([k,*v])
    else:z[:]=[k,*v]
def dumps(a,indent=0):
    if not isinstance(a,list):return json.dumps(str(a),ensure_ascii=False) if isinstance(a,Q) else str(a)
    if not any(isinstance(x,list) for x in a):return '('+' '.join(dumps(x) for x in a)+')'
    s='(';first=True
    for x in a:
        if isinstance(x,list):s+='\n'+'\t'*(indent+1)+dumps(x,indent+1)
        else:s+=('' if first else ' ')+dumps(x)
        first=False
    return s+'\n'+'\t'*indent+')'
def dump(a,p):Path(p).write_text(dumps(a)+'\n',encoding='utf-8')
def props(a):return {x[1]:x[2] for x in children(a,'property')}
