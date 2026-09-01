from __future__ import annotations
from collections import defaultdict
from src.benchmarks.engine import benchmark_for
from src.scoring.confidence import score_confidence

def detect(agg, monthly_metrics, targets, validation):
    findings=[]; seq=1
    byloc=defaultdict(list)
    for r in monthly_metrics: byloc[r['location_id']].append(r)
    def add(loc,metric,current,comparison,source,materiality,evidence,issue_family,inference='low'):
        nonlocal seq
        variance=current-comparison
        conf=score_confidence(validation['data_quality_score'],agg[loc]['months'],source,len(evidence),inference)
        findings.append({'finding_id':f'F-{seq:03d}','location_id':loc,'period':'latest-12-months','metric':metric,'current_value':round(current,3),'comparison_value':round(comparison,3),'variance':round(variance,3),'benchmark_source':source,'materiality':materiality,'confidence':conf,'supporting_evidence':evidence,'issue_family':issue_family}); seq+=1
    for loc,a in agg.items():
        b=benchmark_for('labor_pct',loc,agg,targets)
        if a['labor_pct']-b['value']>1.5:
            ev=[f"Labor {a['labor_pct']:.1f}% vs target {b['value']:.1f}%",f"SPLH ${a['sales_per_labor_hour']:.0f}",f"OT {a['overtime_pct']:.1f}%"]
            add(loc,'labor_pct',a['labor_pct'],b['value'],b['source'],'high' if a['labor_pct']-b['value']>2.5 else 'medium',ev,'labor')
        b=benchmark_for('food_cost_pct',loc,agg,targets)
        if a['food_cost_pct']-b['value']>1.5:
            ev=[f"Food cost {a['food_cost_pct']:.1f}% vs target {b['value']:.1f}%",f"Inventory variance ${a['inventory_variance']:,.0f}"]
            add(loc,'food_cost_pct',a['food_cost_pct'],b['value'],b['source'],'high' if a['food_cost_pct']-b['value']>2.5 else 'medium',ev,'food_control')
        if a['inventory_variance']/a['net_sales']*100 > targets['inventory_variance_pct_sales']:
            comp=targets['inventory_variance_pct_sales']
            add(loc,'inventory_variance_pct_sales',a['inventory_variance']/a['net_sales']*100,comp,'approved_operator_target','high',[f"Inventory variance ${a['inventory_variance']:,.0f}"],'food_control')
        if a['overtime_pct']-targets['overtime_pct']>1.0:
            add(loc,'overtime_pct',a['overtime_pct'],targets['overtime_pct'],'approved_operator_target','medium',[f"OT share {a['overtime_pct']:.1f}%"],'labor')
        rs=sorted(byloc[loc],key=lambda x:x['period'])[-3:]
        if rs:
            denom=sum(x['prior_year_net_sales'] for x in rs); curr=sum(x['net_sales'] for x in rs)
            yoy=(curr-denom)/denom*100 if denom else 0
            if yoy < -5:
                peer_growth=sum(v['sales_growth_pct'] for k,v in agg.items() if k!=loc)/(len(agg)-1)
                add(loc,'sales_growth_pct',yoy,peer_growth,'internal_comparable_location_median','high',[f"Latest 3-month YoY {yoy:.1f}%",f"12-month growth {a['sales_growth_pct']:.1f}%"],'revenue','medium')
    for i in validation['issues']:
        if i.get('location_id'):
            findings.append({'finding_id':f'F-{seq:03d}','location_id':i.get('location_id'),'period':i.get('period','record-level'),'metric':'data_quality','current_value':None,'comparison_value':None,'variance':None,'benchmark_source':'validation_rule','materiality':i['severity'],'confidence':{'score':100,'label':'HIGH','version':'STABILIS-CONFIDENCE-v0.1'},'supporting_evidence':[i['message']],'issue_family':'data_quality'}); seq+=1
    return findings
