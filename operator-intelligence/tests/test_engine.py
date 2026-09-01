from __future__ import annotations
import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from src.ingestion.load import load_raw
from src.validation.engine import validate
from src.normalization.engine import normalize_monthly
from src.metrics.engine import calculate, calculate_all
from src.benchmarks.engine import load_targets, latest_window, aggregate_by_location, benchmark_for
from src.anomalies.engine import detect
from src.opportunities.engine import build
from src.scoring.confidence import score_confidence
class EngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=load_raw(ROOT); cls.val=validate(cls.raw); cls.norm=normalize_monthly(cls.raw['monthly'],cls.val); cls.metrics=calculate_all(cls.norm); cls.window=latest_window(cls.metrics,12); cls.agg=aggregate_by_location(cls.window); cls.targets=load_targets(ROOT); cls.findings=detect(cls.agg,cls.window,cls.targets,cls.val); cls.opps,cls.counted=build(cls.findings,cls.agg,ROOT)
    def test_net_sales_formula(self):
        r=dict(self.norm[0]); m=calculate(r); self.assertAlmostEqual(m['net_sales'],r['gross_sales']-r['discounts']-r['comps']-r['refunds'],places=4)
    def test_labor_formula(self):
        r=self.metrics[0]; self.assertAlmostEqual(r['labor_pct'],r['labor_cost']/r['net_sales']*100,places=6)
    def test_food_cost_formula(self):
        r=self.metrics[0]; self.assertAlmostEqual(r['food_cost_pct'],r['cogs']/r['net_sales']*100,places=6)
    def test_prime_cost_formula(self):
        r=self.metrics[0]; self.assertAlmostEqual(r['prime_cost'],r['labor_cost']+r['cogs'],places=4)
    def test_duplicate_detection(self): self.assertTrue(any(i['type']=='duplicate' for i in self.val['issues']))
    def test_missing_period_detection(self): self.assertTrue(any(i['type']=='missing_period' and i.get('location_id')=='HHR-06' for i in self.val['issues']))
    def test_invalid_value_detection(self): self.assertTrue(any(i['type']=='impossible_value' for i in self.val['issues']))
    def test_conflict_detection(self): self.assertTrue(any(i['type']=='source_conflict' and i.get('location_id')=='HHR-03' for i in self.val['issues']))
    def test_normalization_excludes_invalid(self): self.assertFalse(any(r['source_record_id']=='M-HHR-05-2025-08-01' for r in self.norm))
    def test_benchmark_operator_target(self): self.assertEqual(benchmark_for('labor_pct','HHR-07',self.agg,self.targets)['source'],'approved_operator_target')
    def test_labor_anomalies(self): self.assertTrue({'HHR-07','HHR-08'}.issubset({f['location_id'] for f in self.findings if f['issue_family']=='labor'}))
    def test_food_anomaly(self): self.assertTrue(any(f['location_id']=='HHR-09' and f['issue_family']=='food_control' for f in self.findings))
    def test_sales_decline(self): self.assertTrue(any(f['location_id']=='HHR-10' and f['issue_family']=='revenue' for f in self.findings))
    def test_recoverability_less_than_theoretical(self): self.assertTrue(all(o['realistic_recoverable_opportunity']<=o['theoretical_opportunity'] for o in self.opps))
    def test_dedup_one_primary_per_group(self): self.assertEqual(len({o['opportunity_group_id'] for o in self.counted}),len(self.counted))
    def test_confidence_deterministic(self): self.assertEqual(score_confidence(80,12,'approved_operator_target',2),score_confidence(80,12,'approved_operator_target',2))
    def test_analysis_reproducible(self): self.assertEqual(self.findings,detect(self.agg,self.window,self.targets,self.val))
if __name__=='__main__': unittest.main()
