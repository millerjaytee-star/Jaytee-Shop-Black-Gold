from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / 'operator-intelligence/supabase/migrations/20260901164000_controlled_pilot_product_layer.sql'

def text(name: str) -> str:
    return (ROOT / name).read_text()

def test_public_home_is_product_first_and_financially_safe():
    home=text('index.html')
    assert 'OPERATOR INTELLIGENCE' in home
    assert 'See where margin is moving' in home
    assert 'FICTIONAL' in home and '$392,570.56' in home and 'Verified Value' in home
    assert 'Profit Leak Score' in home and 'Request Diagnostic Review' in home
    assert 'data-netlify' in home

def test_demo_preserves_canonical_financial_contract_and_modules():
    shell=text('operator-intelligence.html');data=text('assets/demo-data.js');app=text('assets/demo.js')
    assert 'FICTIONAL DEMO DATA' in shell
    compact=data.replace(' ','')
    assert 'modeledOpportunity:392570.56' in compact
    assert 'annualized:102844.37' in compact
    assert "kind:'SUPPORTING'" in data and 'annualized:0' in data and 'NOT COUNTED TWICE' in data
    for route in ['command','morning','locations','labor','forecast','inventory','purchasing','food','revenue','opportunities','actions','results','reports','intelligence','alerts','data','expansion','scenarios','weekly','period-close']:
        assert f'#{route}' in shell or route in app

def test_customer_app_uses_authorized_real_data_only():
    shell=text('app.html');js=text('assets/app.js')
    assert 'noindex,nofollow,noarchive' in shell
    assert '/assets/demo-data.js' not in shell
    assert 'stabilis_workspace_payload' in js
    assert 'stabilis_my_organizations' in js and 'stabilis_my_locations' in js
    assert 'stabilis_add_operator_note' in js and 'stabilis_update_onboarding_step' in js
    assert 'service_role' not in shell.lower() and 'service_role' not in js.lower()
    assert '$392,570.56' not in shell and '392570.56' not in js
    assert 'Not enough data' in js
    assert 'STABILIS_ANALYST' in js and 'Customer roles cannot access analyst workspaces' in js

def test_login_recovery_and_browser_key_contract():
    login=text('login.html');config=text('stabilis-config.js')
    assert 'stabilis-config.js' in login
    assert '/auth/v1/token?grant_type=password' in login
    assert '/auth/v1/recover' in login and '/auth/v1/user' in login
    assert 'sessionStorage' in login
    assert 'service_role' not in login.lower() and 'service_role' not in config.lower()
    assert 'supabasePublishableKey' in config

def test_public_trust_and_legal_pages_exist():
    security=text('security.html');privacy=text('privacy.html');terms=text('terms.html')
    assert 'Row Level Security' in security
    assert 'source, report and evidence' in security
    assert 'tenant-scoped' in privacy
    assert 'Modeled opportunity is not verified savings' in terms
    assert '$392,570.56' in terms and 'fictional' in terms.lower()

def test_netlify_security_and_clean_routes():
    redirects=text('_redirects');toml=text('netlify.toml')
    for route in ['/operator-intelligence','/operator-intelligence-report','/login','/app','/security','/privacy','/terms']:
        assert route in redirects
    for header in ['Content-Security-Policy','Strict-Transport-Security','X-Content-Type-Options','X-Robots-Tag']:
        assert header in toml
    assert 'no-store' in toml and 'https://vpunfmwklwjefvchvmpn.supabase.co' in toml

def test_controlled_pilot_product_migration_contract():
    sql=MIGRATION.read_text().lower()
    for table in ['pilot_accounts','onboarding_progress','insight_feedback','operator_notes','usage_events','notification_preferences']:
        assert f'stabilis.{table}' in sql
    for fn in ['stabilis_workspace_payload','stabilis_record_usage_event','stabilis_add_operator_note','stabilis_update_onboarding_step']:
        assert fn in sql
    assert 'counted_in_rollup=true' in sql.replace(' ','')
    assert 'opportunity_kind' in sql and "'primary'" in sql
    assert "verification_status='verified'" in sql.replace(' ','')
    assert 'revoke all on function public.stabilis_workspace_payload' in sql
    assert 'grant execute on function public.stabilis_workspace_payload' in sql

def test_sample_report_preserves_estimated_vs_verified_distinction():
    report=text('operator-intelligence-report.html')
    assert 'FICTIONAL DEMO DATA' in report
    assert '$392,570.56' in report
    assert 'Verified Value = $0' in report
    assert 'HHR-07 overtime is supporting evidence' in report
    assert '$0 additional rollup' in report
