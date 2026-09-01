from __future__ import annotations

def score_confidence(data_quality_score, months, benchmark_source, indicator_count=1, inference='low', recency='current'):
    s=100
    s-=max(0,90-data_quality_score)*0.7
    if months<10:s-=15
    elif months<12:s-=7
    if benchmark_source=='external_industry':s-=12
    elif benchmark_source=='historical':s-=5
    elif benchmark_source=='insufficient_data':s-=35
    if indicator_count>=2:s+=3
    if inference=='medium':s-=8
    elif inference=='high':s-=18
    if recency!='current':s-=8
    s=max(0,min(100,round(s,1)))
    label='HIGH' if s>=85 else 'MEDIUM' if s>=70 else 'LOW' if s>=50 else 'INSUFFICIENT DATA'
    return {'score':s,'label':label,'version':'STABILIS-CONFIDENCE-v0.1'}
