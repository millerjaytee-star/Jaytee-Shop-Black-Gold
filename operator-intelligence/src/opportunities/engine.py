from __future__ import annotations
import json
from pathlib import Path

def build(findings, agg, root):
    rules=json.loads((Path(root)/'config'/'recoverability.json').read_text())
    opportunities=[]
    for f in findings:
        fam=f['issue_family']; loc=f['location_id']
        if fam=='data_quality' or fam not in rules: continue
        a=agg[loc]; theoretical=0.0; target=f['comparison_value']; current=f['current_value']
        if fam=='labor' and f['metric']=='labor_pct': theoretical=max(0,(current-target)/100*a['net_sales'])
        elif fam=='food_control' and f['metric']=='food_cost_pct': theoretical=max(0,(current-target)/100*a['net_sales'])
        elif fam=='food_control' and f['metric']=='inventory_variance_pct_sales': theoretical=max(0,a['inventory_variance']-target/100*a['net_sales'])
        elif fam=='revenue' and f['metric']=='sales_growth_pct':
            gap=max(0,(-2.0-current)/100*a['net_sales']); theoretical=gap
        elif fam=='labor' and f['metric']=='overtime_pct':
            theoretical=max(0,(current-target)/100*a['labor_cost'])
        else: continue
        rr=rules[fam]
        opportunities.append({
          'opportunity_id':'O-'+f['finding_id'][2:],'opportunity_group_id':f'{loc}:{fam}','location_id':loc,'issue_family':fam,'source_finding_id':f['finding_id'],
          'current_performance':current,'target_performance':target,'variance':f['variance'],'relevant_base':round(a['net_sales'] if fam!='labor' or f['metric']!='overtime_pct' else a['labor_cost'],2),
          'theoretical_opportunity':round(theoretical,2),'recoverability_assumption':rr,'low_estimate':round(theoretical*rr['low'],2),
          'realistic_recoverable_opportunity':round(theoretical*rr['base'],2),'high_estimate':round(theoretical*rr['high'],2),'annualized_opportunity':round(theoretical*rr['base'],2),
          'confidence':f['confidence'],'evidence':f['supporting_evidence'],'assumptions':['Latest 12-month operating base','Recoverability rule '+fam],'primary':False,'supporting_indicators':[],'deduplication_rationale':''})
    grouped={}
    for o in opportunities: grouped.setdefault(o['opportunity_group_id'],[]).append(o)
    counted=[]
    for gid,ops in grouped.items():
        primary=max(ops,key=lambda x:x['realistic_recoverable_opportunity'])
        primary['primary']=True
        primary['supporting_indicators']=[x['source_finding_id'] for x in ops if x is not primary]
        if len(ops)>1: primary['deduplication_rationale']='Overlapping indicators in same location/issue family; only highest defensible recoverable amount counted.'
        counted.append(primary)
        for x in ops:
            if x is not primary:
                x['deduplication_rationale']=f"Supporting indicator; excluded from total because {primary['opportunity_id']} is primary for {gid}."
    return opportunities, counted
