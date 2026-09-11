import re,json,collections,math,pathlib
TOKEN=re.compile(r'\s*(\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+)')
def parse(text):
    stack=[]; root=None
    for m in TOKEN.finditer(text):
        t=m.group(1)
        if t=='(':
            n=[]
            if stack:stack[-1].append(n)
            stack.append(n)
        elif t==')':
            root=stack.pop()
        else:stack[-1].append(t)
    assert not stack
    return root
def val(s):
    if isinstance(s,str) and s.startswith('"'):return json.loads(s)
    return s
def nodes(n,k): return [c for c in n if isinstance(c,list) and c and c[0]==k]
def one(n,k,d=None): return next((c for c in n if isinstance(c,list) and c and c[0]==k),d)
def prop(n,k):return next((val(c[2]) for c in nodes(n,'property') if val(c[1])==k),'')
def mm(n,k='at'):return [float(v) for v in one(n,k)[1:]]
def info(path):
    b=parse(pathlib.Path(path).read_text()); fps={}
    for f in nodes(b,'footprint'):
        ref=prop(f,'Reference'); ps=[]
        for p in nodes(f,'pad'):
            ps.append({'pin':val(p[1]),'type':p[2],'shape':p[3],'at':mm(p),'size':mm(p,'size'),'net':val(one(p,'net',['net','0','""'])[-1]),'layers':one(p,'layers')[1:]})
        cr=[]
        for g in f:
            if not isinstance(g,list) or not g:continue
            if g[0] in ['fp_line','fp_rect'] and 'CrtYd' in str(one(g,'layer')):cr.append([mm(g,'start'),mm(g,'end')])
        fps[ref]={'value':prop(f,'Value'),'library':val(f[1]),'at':mm(f),'layer':val(one(f,'layer')[1]),'pads':ps,'courtyard':cr}
    return b,fps
if __name__=='__main__':
    base=pathlib.Path('/mnt/data/pcb_work/layout_relax')
    for name in ['baseline','compact_placed','dirty_study','checked_project/portable_display_epass']:
        b,f=info(base/(name+'.kicad_pcb'));print(name,collections.Counter(n[0] for n in b if isinstance(n,list)))
        print('edges:',[e for e in b if isinstance(e,list) and e[0].startswith('gr_') and 'Edge.Cuts' in str(one(e,'layer'))])
        if name=='compact_placed':
            pathlib.Path('/mnt/data/pcb_work/inventory.json').write_text(json.dumps(f,indent=2))
            for r in sorted(f,key=lambda x:(re.sub(r'\d','',x),int(re.sub(r'\D','',x) or 0))):
                a=f[r]; print(r,a['value'],a['library'],a['at'],a['layer'],'; '.join(p['pin']+':'+p['net'] for p in a['pads']))
