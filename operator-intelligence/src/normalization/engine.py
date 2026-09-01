from __future__ import annotations
from datetime import date

def _f(v):
    try:return float(v)
    except:return None

def normalize_monthly(rows, validation):
    invalid_ids={i.get('record_id') for i in validation['issues'] if i['type'] in {'impossible_value','invalid_value','period_alignment'} and i.get('severity')=='high'}
    out=[]
    for r in rows:
        if r['source_record_id'] in invalid_ids: continue
        try:
            p=date.fromisoformat(r['period'])
            if p.day!=1: continue
        except: continue
        nr={'source':r['source'],'source_record_id':r['source_record_id'],'location_id':r['location_id'],'period':r['period'],'ingestion_timestamp':r['ingestion_timestamp'],'transformation_notes':'numeric coercion; raw preserved'}
        for k,v in r.items():
            if k in nr or k in {'source','source_record_id','location_id','period','ingestion_timestamp'}: continue
            nr[k]=_f(v)
        out.append(nr)
    return out
