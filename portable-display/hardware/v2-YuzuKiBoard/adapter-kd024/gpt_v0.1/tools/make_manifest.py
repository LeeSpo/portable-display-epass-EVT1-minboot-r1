#!/usr/bin/env python3
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parents[1]
rows=[]
for p in sorted(root.rglob('*')):
 if not p.is_file() or p.name=='FILE_MANIFEST.sha256' or any(s in p.parts for s in ['__pycache__','.build']):continue
 rows.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(root).as_posix())
(root/'FILE_MANIFEST.sha256').write_text('\n'.join(rows)+'\n',encoding='utf-8')
print('File manifest written for',len(rows),'files. This is integrity evidence, not design approval.')
