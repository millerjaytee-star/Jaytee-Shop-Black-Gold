from time import perf_counter
from pathlib import Path
import tempfile
from src.persistence.store import Store
from src.persistence.mvp_schema import MVP_SQLITE_SCHEMA

def bench(n):
    with tempfile.TemporaryDirectory() as td:
        s=Store(Path(td)/'bench.sqlite'); s.migrate(); s.db.executescript(MVP_SQLITE_SCHEMA)
        org=s.create_org(f'Bench {n}',f'bench-{n}')
        t=perf_counter()
        for i in range(n):
            s.create_location(org['id'],f'L-{i+1:03d}',f'Location {i+1}')
        insert=perf_counter()-t
        t=perf_counter(); rows=s.all('SELECT * FROM locations WHERE organization_id=?',(org['id'],)); read=perf_counter()-t
        return {'locations':n,'create_seconds':round(insert,4),'read_seconds':round(read,4),'rows':len(rows)}

if __name__=='__main__':
    import json
    out=[bench(n) for n in (10,25,50)]
    p=Path(__file__).resolve().parents[1]/'outputs'/'mvp_performance.json'; p.write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
