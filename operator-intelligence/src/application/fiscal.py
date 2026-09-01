from datetime import date,timedelta
def calendar_months(year):
    out=[]
    for m in range(1,13):
        start=date(year,m,1); end=date(year+1,1,1)-timedelta(days=1) if m==12 else date(year,m+1,1)-timedelta(days=1)
        out.append({'period':f'{year}-{m:02d}','start':start.isoformat(),'end':end.isoformat(),'type':'CALENDAR_MONTH'})
    return out
def four_four_five(year,start):
    out=[]; cur=start
    for i,weeks in enumerate([4,4,5]*4,1):
        end=cur+timedelta(days=weeks*7-1); out.append({'period':f'FY{year}-P{i:02d}','start':cur.isoformat(),'end':end.isoformat(),'weeks':weeks,'type':'4-4-5'}); cur=end+timedelta(days=1)
    return out
