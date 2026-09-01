from __future__ import annotations
METRIC_VERSION='STABILIS-METRIC-v0.1'

def safe_div(a,b,mult=1.0):
    return None if a is None or b in (None,0) else a/b*mult

def calculate(row):
    gross=row['gross_sales']; net=gross-row['discounts']-row['comps']-row['refunds']
    labor=row['hourly_labor_cost']+row['management_labor_cost']+row['overtime_cost']
    cogs=row['food_purchases']+row['beginning_inventory']-row['ending_inventory']+row['waste_cost']
    prime=labor+cogs
    contrib=net-cogs-labor-row['occupancy_cost']-row['other_operating_cost']
    cmr=safe_div(net-cogs-labor,net)
    fixed=row['occupancy_cost']+row['other_operating_cost']
    return {**row,
      'net_sales':net,'sales_growth_pct':safe_div(net-row['prior_year_net_sales'],abs(row['prior_year_net_sales']),100),
      'transactions':row['transactions'],'average_check':safe_div(net,row['transactions']),
      'labor_cost':labor,'labor_pct':safe_div(labor,net,100),'hourly_labor_pct':safe_div(row['hourly_labor_cost'],net,100),
      'management_labor_pct':safe_div(row['management_labor_cost'],net,100),'overtime_pct':safe_div(row['overtime_cost'],labor,100),
      'sales_per_labor_hour':safe_div(net,row['labor_hours']),'labor_cost_per_transaction':safe_div(labor,row['transactions']),
      'cogs':cogs,'food_cost_pct':safe_div(cogs,net,100),'prime_cost':prime,'prime_cost_pct':safe_div(prime,net,100),
      'gross_margin':net-cogs,'location_contribution':contrib,'budget_variance':net-row['budget_net_sales'],
      'budget_variance_pct':safe_div(net-row['budget_net_sales'],abs(row['budget_net_sales']),100),
      'prior_year_variance':net-row['prior_year_net_sales'],'inventory_variance':row['book_inventory']-row['physical_inventory'],
      'inventory_variance_pct_sales':safe_div(row['book_inventory']-row['physical_inventory'],net,100),'waste_pct':safe_div(row['waste_cost'],cogs,100),
      'discount_pct':safe_div(row['discounts'],gross,100),'comp_pct':safe_div(row['comps'],gross,100),'refund_pct':safe_div(row['refunds'],gross,100),
      'revenue_per_location':net,'break_even_sales':safe_div(fixed,cmr),'calculation_version':METRIC_VERSION}

def calculate_all(rows): return [calculate(r) for r in rows]
