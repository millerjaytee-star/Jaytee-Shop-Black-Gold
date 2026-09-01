from __future__ import annotations

def decompose(findings, agg):
    out=[]
    for f in findings:
        if f['issue_family']=='data_quality': continue
        loc=f['location_id']; a=agg[loc]; item={'finding_id':f['finding_id'],'location_id':loc,'issue_family':f['issue_family'],'observed_fact':f['supporting_evidence'][0],'likely_driver':None,'alternative_explanation':None,'requires_verification':True}
        if f['issue_family']=='labor':
            if a['overtime_pct']>4: item['likely_driver']='Elevated overtime contributes to labor variance.'
            else: item['likely_driver']='Excess labor hours / low productivity is more consistent with the observed labor gap than overtime alone.'
            item['alternative_explanation']='Sales denominator weakness or temporary training/opening labor could also elevate labor percentage.'
        elif f['issue_family']=='food_control':
            if a['inventory_variance']>25000: item['likely_driver']='Inventory-control variance is associated with the elevated food-cost signal.'
            else: item['likely_driver']='Purchase cost, waste, portioning or mix may be contributing to the food-cost gap.'
            item['alternative_explanation']='Commodity/vendor price changes or recipe-cost assumptions may explain part of the variance.'
        elif f['issue_family']=='revenue':
            item['likely_driver']='Traffic/check/daypart deterioration is a hypothesis requiring additional decomposition.'
            item['alternative_explanation']='Temporary local demand, closures, construction, competitive openings or data-period effects may contribute.'
        out.append(item)
    return out
