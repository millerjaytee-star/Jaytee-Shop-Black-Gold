from __future__ import annotations
import csv, json, random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
RAW.mkdir(parents=True, exist_ok=True)
random.seed(20260901)

locations = [
    ('HHR-01','Harbor Point','Baltimore, MD','Mid-Atlantic','2018-03-15',5200,'Casual Dining',180,'A. Brooks',1.12),
    ('HHR-02','Capitol Row','Washington, DC','Mid-Atlantic','2019-06-20',4900,'Casual Dining',164,'D. Greene',1.08),
    ('HHR-03','Silver Spring','Silver Spring, MD','Mid-Atlantic','2020-09-11',4550,'Casual Dining',148,'M. Patel',1.00),
    ('HHR-04','Alexandria Wharf','Alexandria, VA','Mid-Atlantic','2021-02-05',5050,'Casual Dining',170,'S. Kim',1.02),
    ('HHR-05','Arlington Commons','Arlington, VA','Mid-Atlantic','2021-11-19',4700,'Casual Dining',156,'J. Cruz',0.99),
    ('HHR-06','Bethesda Lane','Bethesda, MD','Mid-Atlantic','2022-05-13',4600,'Casual Dining',152,'K. James',0.98),
    ('HHR-07','College Park','College Park, MD','Mid-Atlantic','2022-08-26',4400,'Casual Dining',144,'R. Allen',0.96),
    ('HHR-08','Tysons Corner','Tysons, VA','Mid-Atlantic','2023-01-27',5100,'Casual Dining',172,'T. Price',1.04),
    ('HHR-09','National Harbor','Oxon Hill, MD','Mid-Atlantic','2023-04-14',5300,'Casual Dining',176,'L. Morgan',1.03),
    ('HHR-10','Navy Yard','Washington, DC','Mid-Atlantic','2023-09-08',4800,'Casual Dining',160,'C. Davis',1.01),
]
with open(RAW/'locations.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['location_id','name','market','region','opening_date','square_feet','service_model','seating_capacity','manager','sales_index','operating_hours'])
    for row in locations: w.writerow(list(row)+['Mon-Thu 11-22; Fri-Sat 11-23; Sun 11-21'])

months=[]; start=date(2025,1,1)
for i in range(20):
    y=start.year+(start.month-1+i)//12; m=(start.month-1+i)%12+1; months.append(date(y,m,1))
monthly=[]; weekly=[]; inv=[]; vendor=[]
base_monthly_sales=430_000
season={1:.88,2:.90,3:.97,4:1.00,5:1.03,6:1.05,7:1.02,8:.98,9:1.00,10:1.04,11:1.10,12:1.16}
for loc_id,name,market,region,opening,sqft,service,seats,manager,sales_idx in locations:
    prior_sales={}
    for mi,month in enumerate(months):
        trend=1+0.004*mi; noise=random.gauss(1,0.025); sales=base_monthly_sales*sales_idx*season[month.month]*trend*noise
        if loc_id in {'HHR-01','HHR-02'}: sales*=1.035
        if loc_id=='HHR-10' and month>=date(2026,2,1):
            decay=(month.year-2026)*12+month.month-1; sales*=max(.77,1-0.022*decay)
        gross=sales/0.965; disc=gross*random.uniform(.012,.020); comps=gross*random.uniform(.004,.008); refunds=gross*random.uniform(.0015,.0035); net=gross-disc-comps-refunds; tx=int(net/random.uniform(31.5,36.5))
        labor_pct=random.uniform(.300,.325); mgmt_pct=random.uniform(.055,.066); ot_share=random.uniform(.012,.027)
        if loc_id=='HHR-07': labor_pct+=.035; ot_share+=.030
        if loc_id=='HHR-08': labor_pct+=.028; ot_share+=.018
        if loc_id in {'HHR-01','HHR-02'}: labor_pct-=.012
        if loc_id=='HHR-10' and month>=date(2026,2,1): labor_pct+=.008
        labor_cost=net*labor_pct; overtime_cost=labor_cost*ot_share; management_labor=net*mgmt_pct; hourly_labor_cost=max(0,labor_cost-management_labor-overtime_cost); labor_hours=hourly_labor_cost/random.uniform(19.8,22.8)
        food_pct=random.uniform(.285,.303); waste_pct=random.uniform(.010,.018)
        if loc_id=='HHR-09': food_pct+=.042; waste_pct+=.018
        if loc_id in {'HHR-01','HHR-02'}: food_pct-=.008
        cogs=net*food_pct; waste_cost=cogs*waste_pct; beginning_inventory=net*random.uniform(.050,.060); ending_inventory=beginning_inventory*random.uniform(.97,1.04); food_purchases=max(0,cogs-beginning_inventory+ending_inventory-waste_cost); occupancy=net*random.uniform(.075,.090); other=net*random.uniform(.145,.175); budget=net*random.uniform(.99,1.035); py=prior_sales.get(month.month,net/random.uniform(1.02,1.07)); prior_sales[month.month]=net
        book_inv=ending_inventory*random.uniform(.995,1.010); physical_inv=book_inv*random.uniform(.995,1.008)
        if loc_id=='HHR-09': physical_inv=book_inv*random.uniform(.94,.965)
        rec={'source_record_id':f'M-{loc_id}-{month.isoformat()}','location_id':loc_id,'period':month.isoformat(),'gross_sales':round(gross,2),'discounts':round(disc,2),'comps':round(comps,2),'refunds':round(refunds,2),'transactions':tx,'labor_hours':round(labor_hours,2),'hourly_labor_cost':round(hourly_labor_cost,2),'management_labor_cost':round(management_labor,2),'overtime_cost':round(overtime_cost,2),'food_purchases':round(food_purchases,2),'beginning_inventory':round(beginning_inventory,2),'ending_inventory':round(ending_inventory,2),'waste_cost':round(waste_cost,2),'occupancy_cost':round(occupancy,2),'other_operating_cost':round(other,2),'budget_net_sales':round(budget,2),'prior_year_net_sales':round(py,2),'book_inventory':round(book_inv,2),'physical_inventory':round(physical_inv,2),'source':'HHR_monthly_export','ingestion_timestamp':'2026-09-01T00:00:00Z'}
        monthly.append(rec); inv.append({'source_record_id':f'I-{loc_id}-{month.isoformat()}','location_id':loc_id,'period':month.isoformat(),'book_inventory':round(book_inv,2),'physical_inventory':round(physical_inv,2),'count_date':month.isoformat(),'source':'inventory_system','ingestion_timestamp':'2026-09-01T00:00:00Z'}); vendor.append({'source_record_id':f'V-{loc_id}-{month.isoformat()}','location_id':loc_id,'period':month.isoformat(),'food_purchases':round(food_purchases,2),'primary_vendor':'MidAtlantic Foods','price_index':round(100*(1+0.002*mi+random.gauss(0,.006)),2),'source':'ap_export','ingestion_timestamp':'2026-09-01T00:00:00Z'})
        for wk in range(4):
            ws=month+timedelta(days=7*wk); wshare=random.uniform(.235,.265); w_sales=net*wshare; w_hours=labor_hours*wshare
            if loc_id=='HHR-07' and wk in (2,3): w_hours*=1.10
            if loc_id=='HHR-08' and wk==0: w_hours*=1.12
            weekly.append({'source_record_id':f'W-{loc_id}-{ws.isoformat()}','location_id':loc_id,'week_start':ws.isoformat(),'net_sales':round(w_sales,2),'labor_hours':round(w_hours,2),'transactions':int(tx*wshare),'source':'weekly_ops_export','ingestion_timestamp':'2026-09-01T00:00:00Z'})
weekly.append(dict(weekly[137])); weekly=[r for r in weekly if not (r['location_id']=='HHR-06' and r['week_start']=='2026-06-15')]
for r in monthly:
    if r['location_id']=='HHR-05' and r['period']=='2025-08-01': r['transactions']=-41
    if r['location_id']=='HHR-04' and r['period']=='2025-11-01': r['period']='2025-11-15'
    if r['location_id']=='HHR-02' and r['period']=='2026-06-01': r['gross_sales']=round(r['gross_sales']*1.35,2); r['transactions']=int(r['transactions']*1.30)
for r in inv:
    if r['location_id']=='HHR-03' and r['period']=='2026-05-01': r['physical_inventory']=round(r['physical_inventory']*0.965,2)
    if r['location_id']=='HHR-08' and r['period']=='2026-08-01': r['count_date']='2026-04-01'
for r in weekly:
    if r['location_id']=='HHR-03' and r['week_start']=='2026-07-15': r['net_sales']=round(r['net_sales']*1.50,2)
def write_csv(path, rows):
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
write_csv(RAW/'monthly_operations.csv',monthly); write_csv(RAW/'weekly_operations.csv',weekly); write_csv(RAW/'inventory.csv',inv); write_csv(RAW/'vendor_purchases.csv',vendor)
ground_truth={'company':'Harbor & Hearth Restaurant Group','analysis_must_not_read_this_file':True,'seeded_operating_conditions':[{'location_id':'HHR-01','type':'strong_performer'},{'location_id':'HHR-02','type':'strong_performer'},{'location_id':'HHR-07','type':'labor_problem','severity':'high'},{'location_id':'HHR-08','type':'labor_problem','severity':'moderate'},{'location_id':'HHR-09','type':'food_inventory_problem','severity':'high'},{'location_id':'HHR-10','type':'declining_sales','severity':'high'}],'average_locations':['HHR-03','HHR-04','HHR-05','HHR-06'],'seeded_data_quality_issues':['duplicate weekly import record','missing weekly period HHR-06 Jun 2026','negative transactions HHR-05 Aug 2025','period alignment HHR-04 Nov 2025','legitimate sales outlier HHR-02 Jun 2026','inventory source conflict HHR-03 May 2026','stale inventory HHR-08 Aug 2026','weekly/monthly reconciliation issue HHR-03 Jul 2026']}
(ROOT/'data').mkdir(exist_ok=True)
(ROOT/'data'/'ground_truth.json').write_text(json.dumps(ground_truth,indent=2))
print(f'Generated {len(monthly)} monthly rows, {len(weekly)} weekly rows, {len(inv)} inventory rows')
