from pathlib import Path
from fastapi.testclient import TestClient
from src.api.app import app
ROOT=Path(__file__).resolve().parents[2]
REPO=ROOT.parent
MIG=(ROOT/'supabase/migrations/202609010003_full_platform_schema.sql')

def test_health_and_protection():
    c=TestClient(app); assert c.get('/health').status_code==200; assert c.get('/api/orgs/nope/dashboard').status_code==401

def test_required_docs():
    for p in ['../../docs/architecture.md','../../docs/database.md','../../docs/intelligence-engine.md','../../docs/security-release-gate.md','../../docs/operator-intelligence-v1.md','../../docs/deployment.md']:
        assert (ROOT/p).resolve().exists(), p

def test_public_demo_contract():
    demo=(REPO/'operator-intelligence.html').read_text(); report=(REPO/'operator-intelligence-report.html').read_text(); login=(REPO/'login.html').read_text(); home=(REPO/'index.html').read_text()
    assert 'FICTIONAL DEMO DATA' in demo and '$392,570.56' in demo and 'SUPPORTING · NOT COUNTED TWICE' in demo and 'VERIFIED STABILIS-ATTRIBUTABLE VALUE · $0' in demo
    for anchor in ['#locations','#opportunities','#hhr07','#labor','#food','#revenue','#actions','#results','#data','#reports']: assert anchor in demo
    assert 'Modeled Recoverable' in report and 'Verified Value' in report and '$392,570.56' in report
    assert 'REAL FINANCIAL DATA RELEASE GATE = BLOCKED' in login
    for token in ['Stabilize. Systemize. Scale.','/operator-intelligence','Profit Leak Score','/sample-intelligence','/login','stabilis-lead']: assert token in home

def test_full_schema_contract():
    sql=MIG.read_text().lower()
    required=['organization_profiles','invitations','location_groups','operating_targets','benchmarks','data_sources','integrations','import_batches','column_mappings','validation_errors','data_quality_checks','fact_sales','fact_labor','fact_inventory','metric_definitions','score_definitions','opportunity_evidence','opportunity_scenarios','recommendation_versions','confidence_assessments','action_updates','observed_results','verified_values','verification_reviews','report_runs','report_versions','generated_documents','processing_logs','system_events','feature_flags']
    for t in required: assert f'stabilis.{t}' in sql
    assert 'create extension if not exists citext' in sql
    assert 'canonical_opportunity_rollup' in sql and "opportunity_kind = 'primary'" in sql and 'counted_in_rollup' in sql
    assert "'stabilis-reports','stabilis-reports',false" in sql and "'stabilis-evidence','stabilis-evidence',false" in sql

def test_release_gate_stays_blocked_until_live_security():
    doc=(REPO/'docs/security-release-gate.md').read_text(); assert 'REAL FINANCIAL DATA RELEASE GATE = BLOCKED' in doc; assert '$392,570.56' in doc
