from __future__ import annotations
from dataclasses import dataclass
CANONICAL_ALIASES={'net_sales':{'net sales','net rev','revenue','sales net','netsales'},'labor_cost':{'labor cost','labour cost','wages','total labor'},'cogs':{'cogs','cost of goods sold','food cost dollars','product cost'},'transactions':{'transactions','checks','guest checks','orders'},'labor_hours':{'labor hours','hours worked','worked hours'},'budget_sales':{'budget sales','sales budget','budgeted sales'}}
@dataclass(frozen=True)
class Suggestion: source:str; target:str|None; confidence:float; requires_review:bool
def normalize(s): return ' '.join(str(s).lower().replace('_',' ').split())
def suggest_column(source):
    n=normalize(source); exact=[k for k,v in CANONICAL_ALIASES.items() if n in v or n==normalize(k)]
    if len(exact)==1:return Suggestion(source,exact[0],0.99,False)
    tokens=set(n.split()); best=(None,0.0)
    for target,aliases in CANONICAL_ALIASES.items():
        for a in aliases:
            at=set(a.split()); score=len(tokens&at)/max(len(tokens|at),1)
            if score>best[1]: best=(target,score)
    conf=round(best[1],2); return Suggestion(source,best[0] if conf>=0.34 else None,conf,conf<0.8)
def resolve_location(value,aliases):
    key=normalize(value); matches={v for k,v in aliases.items() if normalize(k)==key}
    if len(matches)==1:return next(iter(matches))
    raise ValueError('LOCATION RESOLUTION REQUIRED')
