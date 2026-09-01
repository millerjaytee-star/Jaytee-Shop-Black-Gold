def pct_change(current,prior):
    if prior in (None,0): return None
    return (current-prior)/abs(prior)*100
def trend_series(rows,metric,location_id=None):
    vals=sorted([r for r in rows if location_id is None or r.get('location_id')==location_id],key=lambda r:r['period']); out=[]
    for i,r in enumerate(vals):
        v=r.get(metric); prev=vals[i-1].get(metric) if i else None
        out.append({'period':r['period'],'value':v,'period_change_pct':pct_change(v,prev) if v is not None and prev is not None else None})
    return out
def alerts_from_aggregates(aggregates,targets):
    alerts=[]
    for loc,a in aggregates.items():
        for metric,val,target,kind in [('labor_pct',a.get('labor_pct'),targets.get('labor_pct'),'LABOR_ABOVE_TARGET'),('food_cost_pct',a.get('food_cost_pct'),targets.get('food_cost_pct'),'FOOD_COST_DETERIORATION')]:
            if val is not None and target is not None and val>target+1.0: alerts.append({'location_id':loc,'type':kind,'metric':metric,'current':val,'target':target,'materiality':round(val-target,2),'status':'OPEN'})
    return alerts
