from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

def load_targets(root):
    return json.loads((Path(root)/'config'/'targets.json').read_text())

def latest_window(metrics, months=12):
    periods=sorted({r['period'] for r in metrics})
    keep=set(periods[-months:])
    return [r for r in metrics if r['period'] in keep]

def aggregate_by_location(rows):
    by=defaultdict(list)
    for r in rows: by[r['location_id']].append(r)
    out={}
    for loc,rs in by.items():
        net=sum(x['net_sales'] for x in rs); labor=sum(x['labor_cost'] for x in rs); cogs=sum(x['cogs'] for x in rs)
        ot=sum(x['overtime_cost'] for x in rs); hrs=sum(x['labor_hours'] for x in rs); tx=sum(x['transactions'] for x in rs if x['transactions'] is not None and x['transactions']>0)
        out[loc]={
          'months':len(rs),'net_sales':net,'labor_cost':labor,'labor_pct':labor/net*100,'cogs':cogs,'food_cost_pct':cogs/net*100,
          'prime_cost_pct':(labor+cogs)/net*100,'overtime_pct':ot/labor*100,'sales_per_labor_hour':net/hrs,
          'transactions':tx,'average_check':net/tx if tx else None,'location_contribution':sum(x['location_contribution'] for x in rs),
          'budget_variance_pct':sum(x['budget_variance'] for x in rs)/sum(x['budget_net_sales'] for x in rs)*100,
          'sales_growth_pct':sum(x['net_sales']-x['prior_year_net_sales'] for x in rs)/sum(x['prior_year_net_sales'] for x in rs)*100,
          'inventory_variance':sum(max(0,x['inventory_variance']) for x in rs),'waste_cost':sum(x['waste_cost'] for x in rs),
          'discounts':sum(x['discounts'] for x in rs),'comps':sum(x['comps'] for x in rs),'refunds':sum(x['refunds'] for x in rs),
          'gross_sales':sum(x['gross_sales'] for x in rs)}
    return out

def benchmark_for(metric, loc, agg, targets):
    target_key={'labor_pct':'labor_pct','food_cost_pct':'food_cost_pct','prime_cost_pct':'prime_cost_pct','overtime_pct':'overtime_pct'}.get(metric)
    if target_key:
        return {'value':targets[target_key],'source':'approved_operator_target'}
    peers=[v[metric] for k,v in agg.items() if k!=loc and v.get(metric) is not None]
    return {'value':median(peers),'source':'internal_comparable_location_median'} if peers else {'value':None,'source':'insufficient_data'}
