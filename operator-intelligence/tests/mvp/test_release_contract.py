from pathlib import Path
from fastapi.testclient import TestClient
from src.api.app import app

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
MIG = ROOT / 'supabase/migrations/202609010003_full_platform_schema.sql'
CUSTOMER_CONTEXT_MIG = ROOT / 'supabase/migrations/202609010004_public_customer_context.sql'


def test_health_and_protection():
    c = TestClient(app)
    assert c.get('/health').status_code == 200
    assert c.get('/api/orgs/nope/dashboard').status_code == 401


def test_required_docs():
    for name in ['architecture.md','database.md','intelligence-engine.md','security-release-gate.md','operator-intelligence-v1.md','deployment.md']:
        assert (REPO / 'docs' / name).exists(), name


def test_public_demo_contract():
    demo = (REPO / 'operator-intelligence.html').read_text()
    demo_data = (REPO / 'assets/demo-data.js').read_text()
    demo_app = (REPO / 'assets/demo.js').read_text()
    report = (REPO / 'operator-intelligence-report.html').read_text()
    login = (REPO / 'login.html').read_text()
    secure_app = (REPO / 'app.html').read_text()
    secure_js = (REPO / 'assets/app.js').read_text()
    config = (REPO / 'stabilis-config.js').read_text()
    home = (REPO / 'index.html').read_text()
    gate = (REPO / 'docs/security-release-gate.md').read_text()

    assert 'FICTIONAL DEMO DATA' in demo
    assert 'modeledOpportunity:392570.56' in demo_data.replace(' ','')
    assert "kind:'SUPPORTING'" in demo_data and 'NOT COUNTED TWICE' in demo_data
    assert 'verifiedValue:0' in demo_data.replace(' ','')
    for anchor in ['#locations','#opportunities','#labor','#food','#revenue','#actions','#results','#data','#reports']:
        assert anchor in demo
    assert 'HHR-07' in demo_data and '102844.37' in demo_data
    assert 'location/' in demo_app

    assert 'Modeled Recoverable' in report
    assert 'Verified Value' in report
    assert '$392,570.56' in report

    assert 'stabilis-config.js' in login
    assert 'stabilis-config.js' in secure_app
    assert 'https://vpunfmwklwjefvchvmpn.supabase.co' not in login
    assert 'service_role' not in login.lower()
    assert 'service_role' not in secure_app.lower()
    assert 'service_role' not in secure_js.lower()
    assert 'supabaseUrl' in config and 'supabasePublishableKey' in config
    assert 'service_role' not in config.lower()

    # Recovery/invitation/session behavior is now shared through dedicated browser assets.
    assert "t==='recovery'" in login
    assert '/auth/v1/recover' in login
    assert "method:'PUT'" in login and '/auth/v1/user' in login
    assert 'newPassword' in login and 'confirmPassword' in login
    assert 'consume()' in secure_js
    assert 'access_token' in secure_js and 'refresh_token' in secure_js
    assert 'grant_type=refresh_token' in secure_js
    assert 'stabilis_my_organizations' in secure_js
    assert 'stabilis_my_locations' in secure_js
    assert 'stabilis_workspace_payload' in secure_js

    assert 'Stabilize. Systemize. Scale.' in home
    assert 'Profit Leak Score' in home
    assert 'Book a Diagnostic' in home
    for required_surface in ['operator-intelligence.html','operator-intelligence-report.html','login.html','app.html']:
        assert (REPO / required_surface).exists(), required_surface

    assert 'CONTROLLED PILOT FINANCIAL DATA RELEASE GATE = PASSED' in gate


def test_full_schema_contract():
    sql = MIG.read_text().lower()
    required = ['organization_profiles','invitations','location_groups','operating_targets','benchmarks','data_sources','integrations','import_batches','column_mappings','validation_errors','data_quality_checks','fact_sales','fact_labor','fact_inventory','metric_definitions','score_definitions','opportunity_evidence','opportunity_scenarios','recommendation_versions','confidence_assessments','action_updates','observed_results','verified_values','verification_reviews','report_runs','report_versions','generated_documents','processing_logs','system_events','feature_flags','forecast_models','forecast_runs','forecast_inputs','forecast_values','forecast_accuracy','user_preferences','widget_preferences']
    for table in required:
        assert f'stabilis.{table}' in sql
    assert 'create extension if not exists citext' in sql
    assert 'canonical_opportunity_rollup' in sql and "opportunity_kind = 'primary'" in sql and 'counted_in_rollup' in sql
    assert "'stabilis-reports','stabilis-reports',false" in sql
    assert "'stabilis-evidence','stabilis-evidence',false" in sql


def test_public_customer_context_contract():
    sql = CUSTOMER_CONTEXT_MIG.read_text().lower()
    assert 'security_invoker = true' in sql
    assert 'public.stabilis_my_organizations' in sql
    assert 'public.stabilis_my_locations' in sql
    assert 'm.profile_id = auth.uid()' in sql
    assert 'stabilis.can_access_location' in sql
    assert 'revoke all' in sql and 'from public, anon' in sql
    assert 'grant select' in sql and 'to authenticated' in sql


def test_controlled_pilot_release_gate_is_closed_with_proof():
    doc = (REPO / 'docs/security-release-gate.md').read_text()
    assert 'CONTROLLED PILOT FINANCIAL DATA RELEASE GATE = PASSED' in doc
    assert 'Session refresh using the refresh token: PASS' in doc
    assert 'Invitation acceptance session: PASS' in doc
    assert 'Active organization membership resolution: PASS' in doc
    assert 'Direct cross-tenant organization-ID guess: PASS' in doc
    assert 'Temporary QA users and tenant data: REMOVED' in doc
    assert '$392,570.56' in doc
