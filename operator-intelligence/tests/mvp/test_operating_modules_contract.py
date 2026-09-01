from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_customer_app_loads_completed_module_layer():
    app = read("app.html")
    assert '/assets/app-modules.js' in app
    for anchor in ["#morning", "#labor", "#forecast", "#inventory", "#purchasing", "#food", "#revenue", "#weekly", "#period-close", "#expansion"]:
        assert anchor in app


def test_domain_desks_use_authorized_intelligence_context_and_empty_states():
    js = read("assets/app-modules.js")
    assert "stabilis_intelligence_context" in js
    for name in ["Labor Intelligence", "Revenue Intelligence", "Inventory Intelligence", "Food Cost Intelligence", "Purchasing Intelligence"]:
        assert name in js
    assert "Not enough data" in js
    assert "authorized" in js.lower()


def test_secure_upload_is_private_tenant_scoped_and_checksum_guarded():
    js = read("assets/app-modules.js")
    assert "crypto.subtle.digest('SHA-256'" in js
    assert "stabilis_register_raw_upload" in js
    assert "stabilis_set_raw_upload_state" in js
    assert "/storage/v1/object/stabilis-raw/" in js
    assert "x-upsert':'false'" in js
    assert "Duplicate file detected by checksum" in js
    sql = read("operator-intelligence/supabase/migrations/20260901222500_secure_upload_state_machine.sql")
    assert "PENDING_UPLOAD" in sql
    assert "only CSV or XLSX" in sql
    assert "52428800" in sql
    assert "split_part(p_storage_path,'/',1) <> p_organization_id::text" in sql


def test_actions_require_analyst_approved_recommendation_and_verification_role():
    sql = read("operator-intelligence/supabase/migrations/20260901222000_pilot_interaction_rpcs.sql")
    assert "ANALYST_APPROVED" in sql and "ANALYST_EDITED" in sql
    assert "analyst-approved recommendation required" in sql
    assert "verification requires Stabilis reviewer" in sql
    assert "expected_financial_impact" in sql
    assert "coalesce(v_opp.base_estimate,v_opp.annualized_value)" in sql


def test_review_briefs_keep_financial_stages_separate():
    js = read("assets/app-modules.js")
    assert "Modeled Opportunity" in js
    assert "Verified Value" in js
    assert "Weekly Operating Review" in js
    assert "Watch · Act · Verify" in js
    assert "No mystery AI scoring" in js
