from __future__ import annotations
from pathlib import Path
import csv, re
ALLOWED_EXTENSIONS={'.csv','.xlsx'}
MAX_UPLOAD_BYTES=25*1024*1024
DANGEROUS_FORMULA_PREFIXES=('=','+','-','@')
def safe_filename(name:str)->str:
    base=Path(name).name
    base=re.sub(r'[^A-Za-z0-9._-]+','_',base)
    if base in ('','.','..'): raise ValueError('invalid filename')
    return base[:180]
def validate_upload(path):
    p=Path(path)
    if p.suffix.lower() not in ALLOWED_EXTENSIONS: raise ValueError('unsupported file type')
    if p.stat().st_size>MAX_UPLOAD_BYTES: raise ValueError('file too large')
    if p.suffix.lower()=='.csv':
        try: text=p.read_bytes().decode('utf-8-sig')
        except UnicodeDecodeError as e: raise ValueError('unsupported encoding') from e
        rows=list(csv.reader(text.splitlines()))
        if not rows: raise ValueError('empty file')
        headers=rows[0]
        if len(headers)!=len(set(h.strip().lower() for h in headers)): raise ValueError('duplicate headers')
        for row in rows[1:]:
            for cell in row:
                if isinstance(cell,str) and cell.lstrip().startswith(DANGEROUS_FORMULA_PREFIXES): raise ValueError('formula-like cell rejected')
    return {'filename':safe_filename(p.name),'size':p.stat().st_size,'extension':p.suffix.lower()}
