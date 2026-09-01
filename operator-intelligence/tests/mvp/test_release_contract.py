from pathlib import Path
from fastapi.testclient import TestClient
from src.api.app import app

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
MIG = ROOT / 'supabase/migrations/202609010003_full_platform_schema.sql'


def test_health_and_protection():
    c = TestClient(app)
    assert c.get('/health').status_code == 200
    assert c.get('/api/orgs/nope/dashboard').status_code == 401


def test_required_docs():
    for name in [
        'architecture.md',
        'database.md',
        'intelligence-engine.md',
        'security-release-gate.md',
        'operator-intelligence-v1.md',
        'deployment.md',
    ]:
        assert (REPO / 'docs' / name).exists(), name


def test_public_demo_contract():
    demo = (REPO / 'operator-intelligence.html').read_text()
    report = (REPO / 'operator-intelligence-report.html').read_text()
    login = (REPO / 'login.html').read_text()
    config = (REPO / 'stabilis-config.js').read_text()
    home = (REPO / 'index.html').read_text()
    gate = (REPO / 'docs/security-release-gate.md').read_text()

    assert 'FICTIONAL DEMO DATA' in demo
    assert '$392,570.56' in demo
    assert 'SUPPORTING · NOT COUNTED TWICE' in demo
    assert 'VERIFIED STABILIS-ATTRIBUTABLE VALUE · $0' in demo
    for anchor in ['#locations', '#opportunities', '#hhr07', '#labor', '#food', '#revenue', '#actions', '#results', '#data', '#reports']:
        assert anchor in demo

    assert 'Modeled Recoverable' in report
    assert 'Verified Value' in report
    assert '$392,570.56' in report

    # Login must consume shared config rather than embed a project URL or privileged key.
    assert 'stabilis-config.js' in login
    assert 'https://vpunfmwklwjefvchvmpn.supabase.co' not in login
    assert 'service_role' not in login.lower()
    assert 'supabaseUrl' in config and 'supabasePublishableKey' in config
    assert 'service_role' not in config.lower()

    # Public home remains the sales/diagnostic surface; secure/demo routes are independently deployable.
    assert 'Stabilize. Systemize. Scale.' in home
    assert 'Profit Leak Score' in home
    assert 'Book an Operations Conversation' in home
    for required_surface in ['operator-intelligence.html', 'operator-intelligence-report.html', 'login.html', 'app.html']:
        assert (REPO / required_surface).exists(), required_surface

    assert 'REAL FINANCIAL DATA RELEASE GATE = BLOCKED' in gate


def test_full_schema_contract():
    sql = MIG.read_text().lower()
    required = [
        'organization_profiles', 'invitations', 'location_groups', 'operating_targets', 'benchmarks', 'data_sources',
        'integrations', 'import_batches', 'column_mappings', 'validation_errors', 'data_quality_checks', 'fact_sales',
        'fact_labor', 'fact_inventory', 'metric_definitions', 'score_definitions', 'opportunity_evidence',
        'opportunity_scenarios', 'recommendation_versions', 'confidence_assessments', 'action_updates',
        'observed_results', 'verified_values', 'verification_reviews', 'report_runs', 'report_versions',
        'generated_documents', 'processing_logs', 'system_events', 'feature_flags', 'forecast_models', 'forecast_runs',
        'forecast_inputs', 'forecast_values', 'forecast_accuracy', 'user_preferences', 'widget_preferences',
    ]
    for table in required:
        assert f'stabilis.{table}' in sql
    assert 'create extension if not exists citext' in sql
    assert 'canonical_opportunity_rollup' in sql and "opportunity_kind = 'primary'" in sql and 'counted_in_rollup' in sql
    assert "'stabilis-reports','stabilis-reports',false" in sql
    assert "'stabilis-evidence','stabilis-evidence',false" in sql


def test_release_gate_stays_blocked_until_positive_auth_validation():
    doc = (REPO / 'docs/security-release-gate.md').read_text()
    assert 'REAL FINANCIAL DATA RELEASE GATE = BLOCKED' in doc
    assert '$392,570.56' in doc
