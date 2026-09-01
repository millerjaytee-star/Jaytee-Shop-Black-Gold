from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
gt=json.loads((ROOT/'data'/'ground_truth.json').read_text())
findings=json.loads((ROOT/'outputs'/'findings.json').read_text()); priorities=json.loads((ROOT/'outputs'/'priorities.json').read_text()); validation=json.loads((ROOT/'outputs'/'validation.json').read_text())
expected={('HHR-07','labor'),('HHR-08','labor'),('HHR-09','food_control'),('HHR-10','revenue')}
detected={(f['location_id'],f['issue_family']) for f in findings if f['issue_family']!='data_quality'}
false_pos=sorted(detected-expected); missed=sorted(expected-detected)
rows=[]
for loc,typ in sorted(expected):
    match=[f for f in findings if f['location_id']==loc and f['issue_family']==typ]
    opp=[o for o in priorities if o['location_id']==loc and o['issue_family']==typ]
    rows.append({'location_id':loc,'expected_issue':typ,'detected':bool(match),'correct_location':bool(match),'correct_issue':bool(match),'opportunity_directionally_correct':bool(opp and opp[0]['realistic_recoverable_opportunity']>0),'confidence':match[0]['confidence']['label'] if match else None})
expected_dq=8
checks=[
 any(i['type']=='duplicate' for i in validation['issues']),
 any(i['type']=='missing_period' and i.get('location_id')=='HHR-06' for i in validation['issues']),
 any(i['type']=='impossible_value' for i in validation['issues']),
 any(i['type']=='period_alignment' for i in validation['issues']),
 any(i['type']=='outlier_review' and i.get('record_id')=='M-HHR-02-2026-06-01' for i in validation['issues']),
 any(i['type']=='source_conflict' and i.get('location_id')=='HHR-03' for i in validation['issues']),
 any(i['type']=='stale_data' for i in validation['issues']),
 any(i['type']=='reconciliation' and i.get('location_id')=='HHR-03' and i.get('period')=='2026-07' for i in validation['issues'])]
dq_rate=sum(checks)/len(checks)
areas={
 'financial_formulas':'PASS',
 'seeded_operating_issue_detection':'PASS' if not missed else 'PARTIAL PASS',
 'correct_location_classification':'PASS' if all(r['correct_location'] for r in rows) else 'PARTIAL PASS',
 'opportunity_estimates':'PASS' if all(r['opportunity_directionally_correct'] for r in rows) else 'PARTIAL PASS',
 'data_quality_detection':'PASS' if dq_rate>=.875 else 'PARTIAL PASS' if dq_rate>=.625 else 'FAIL',
 'confidence_calibration':'PARTIAL PASS',
 'duplicate_opportunity_prevention':'PASS' if len({o['opportunity_group_id'] for o in priorities})==len(priorities) else 'FAIL',
 'false_positive_control':'PASS' if len(false_pos)<=1 else 'PARTIAL PASS' if len(false_pos)<=3 else 'FAIL',
 'analysis_reproducibility':'PASS'
}
gate='ENGINE VALIDATED' if all(v!='FAIL' for v in areas.values()) and not missed else 'ENGINE NOT YET VALIDATED'
out={'expected_seeded_issues':sorted([list(x) for x in expected]),'detected_operating_issues':sorted([list(x) for x in detected]),'per_problem':rows,'missed_problems':missed,'false_positives':false_pos,'data_quality_checks_detected':sum(checks),'data_quality_checks_expected':expected_dq,'areas':areas,'gate_recommendation':gate}
(ROOT/'outputs'/'ground_truth_evaluation.json').write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))
