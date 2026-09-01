from __future__ import annotations

def prioritize(counted):
    if not counted:return []
    max_imp=max(o['realistic_recoverable_opportunity'] for o in counted) or 1
    result=[]
    for o in counted:
        impact=o['realistic_recoverable_opportunity']/max_imp*100
        conf=o['confidence']['score']
        fam=o['issue_family']
        effort={'labor':60,'food_control':55,'revenue':35}.get(fam,50)
        time={'labor':85,'food_control':75,'revenue':50}.get(fam,60)
        control={'labor':90,'food_control':85,'revenue':55}.get(fam,60)
        risk=75 if fam in {'labor','food_control'} else 55
        dependency=80 if fam in {'labor','food_control'} else 60
        score=.30*impact+.20*conf+.10*(100-effort)+.15*time+.15*control+.05*risk+.05*dependency
        cat='QUICK WIN' if score>=78 and effort<=60 else 'HIGH PRIORITY' if score>=68 else 'STRATEGIC' if score>=55 else 'MONITOR'
        x=dict(o); x.update(priority_score=round(score,1),priority_category=cat,implementation_effort=effort,time_to_impact=time,management_control=control)
        result.append(x)
    return sorted(result,key=lambda x:x['priority_score'],reverse=True)
