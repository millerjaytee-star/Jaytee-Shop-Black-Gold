from __future__ import annotations
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.ingestion.load import load_raw
from src.validation.engine import validate
from src.normalization.engine import normalize_monthly
from src.metrics.engine import calculate_all
from src.benchmarks.engine import load_targets, latest_window, aggregate_by_location
from src.anomalies.engine import detect
from src.anomalies.root_cause import decompose
from src.opportunities.engine import build
from src.scoring.priority import prioritize
from src.scoring.operator import operator_scores
from src.reporting.report import generate

(ROOT/'outputs').mkdir(parents=True,exist_ok=True)
(ROOT/'data'/'normalized').mkdir(parents=True,exist_ok=True)

raw=load_raw(ROOT); val=validate(raw); norm=normalize_monthly(raw['monthly'],val); metrics=calculate_all(norm)
window=latest_window(metrics,12); agg=aggregate_by_location(window); targets=load_targets(ROOT)
findings=detect(agg,window,targets,val); root_causes=decompose(findings,agg); opps,counted=build(findings,agg,ROOT); priorities=prioritize(counted); scores=operator_scores(agg,counted,val['data_quality_score'])

def dump(name,obj): (ROOT/'outputs'/name).write_text(json.dumps(obj,indent=2))
dump('validation.json',val); dump('findings.json',findings); dump('root_cause_decomposition.json',root_causes); dump('opportunities_all.json',opps); dump('opportunities_counted.json',counted); dump('priorities.json',priorities); dump('scores.json',scores); dump('location_aggregates.json',agg)
if norm:
    with open(ROOT/'data'/'normalized'/'monthly_operations_normalized.csv','w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(norm[0].keys())); w.writeheader(); w.writerows(norm)
report=generate(scores,val,agg,priorities,counted,findings); (ROOT/'outputs'/'operator_intelligence_report.md').write_text(report)
print(json.dumps({'data_quality':val['data_quality_score'],'findings':len(findings),'counted_opportunities':len(counted),'recoverable_total':sum(o['realistic_recoverable_opportunity'] for o in counted),'scores':scores,'top_priorities':[(o['location_id'],o['issue_family'],o['realistic_recoverable_opportunity']) for o in priorities[:5]]},indent=2))
