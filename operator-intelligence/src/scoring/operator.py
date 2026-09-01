from __future__ import annotations

def clamp(x): return max(0,min(100,x))
def operator_scores(agg, counted, data_quality):
    total_sales=sum(a['net_sales'] for a in agg.values())
    leak=sum(o['realistic_recoverable_opportunity'] for o in counted)
    leak_rate=leak/total_sales*100 if total_sales else 0
    profit_leak=clamp(leak_rate/4*100)
    labor_pen=sum(max(0,a['labor_pct']-31.5) for a in agg.values())/len(agg)
    food_pen=sum(max(0,a['food_cost_pct']-29.5) for a in agg.values())/len(agg)
    rev_pen=sum(max(0,-a['sales_growth_pct']) for a in agg.values())/len(agg)
    labor=clamp(100-labor_pen*12); food=clamp(100-food_pen*12); revenue=clamp(100-rev_pen*6)
    financial=clamp(100-(labor_pen+food_pen)*5-rev_pen*2)
    consistency=clamp(100-(max(a['labor_pct'] for a in agg.values())-min(a['labor_pct'] for a in agg.values()))*5)
    management=clamp((labor+food)/2)
    health=.25*financial+.20*labor+.20*food+.15*revenue+.10*consistency+.10*management
    return {'operator_health_score':round(health,1),'profit_leak_score':round(profit_leak,1),'labor_efficiency_score':round(labor,1),'food_inventory_control_score':round(food,1),'revenue_quality_score':round(revenue,1),'financial_health_score':round(financial,1),'operating_consistency_score':round(consistency,1),'management_execution_score':round(management,1),'data_quality_score':data_quality,'version':'STABILIS-SCORE-v0.1'}
