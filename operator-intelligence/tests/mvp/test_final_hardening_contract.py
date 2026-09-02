import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def load(path: str):
    return json.loads(read(path))


def test_golden_suite_is_versioned_and_covers_required_cases():
    spec = load("operator-intelligence/evals/ask_stabilis_golden_v1.json")
    assert spec["evaluation_version"] == "ask-stabilis-golden-v1"
    assert spec["prompt_version"] == "ask-stabilis-v2-telemetry"
    assert len(spec["cases"]) >= 15
    ids = {case["id"] for case in spec["cases"]}
    assert {
        "EXEC-001", "LABOR-001", "FIN-001", "HHR07-001", "DEDUPE-001",
        "VERIFY-001", "FALSESAVE-001", "DQ-001", "ACTION-001", "CONF-001",
        "NODATA-001", "TENANT-001", "LOCATION-001", "INJECT-001", "SECRET-001",
    } <= ids
    critical = {case["id"] for case in spec["cases"] if case["critical"]}
    assert {"FIN-001", "HHR07-001", "DEDUPE-001", "VERIFY-001", "FALSESAVE-001"} <= critical
    assert {"TENANT-001", "LOCATION-001", "INJECT-001", "SECRET-001"} <= critical


def test_golden_fixture_preserves_financial_truth_and_scope():
    ctx = load("operator-intelligence/evals/harbor_hearth_eval_context_v1.json")
    assert ctx["fictional"] is True
    assert ctx["kpis"]["modeled_opportunity"] == 392570.56
    assert ctx["kpis"]["verified_value"] == 0
    opportunities = {row["id"]: row for row in ctx["opportunities"]}
    assert opportunities["HHR07-LABOR-01"]["recoverable_amount"] == 102844.37
    assert opportunities["HHR07-LABOR-01"]["kind"] == "PRIMARY"
    assert opportunities["HHR07-OT-01"]["additive_amount"] == 0
    assert opportunities["HHR07-OT-01"]["kind"] == "SUPPORTING"
    assert opportunities["HHR07-OT-01"]["counted_in_rollup"] is False
    assert "HHR-01" not in ctx["context"]["authorized_locations"]
    assert "416284.30" not in json.dumps(ctx)


def test_telemetry_migration_uses_provider_usage_and_internal_only_read_access():
    sql = read("operator-intelligence/supabase/migrations/20260902003000_ask_stabilis_telemetry_hardening.sql")
    for column in [
        "input_tokens", "cached_input_tokens", "output_tokens", "total_tokens",
        "approximate_cost_usd", "estimated_netlify_credits", "pricing_version", "model_version",
    ]:
        assert column in sql
    assert "stabilis_begin_intelligence_query" in sql
    assert "stabilis_finalize_intelligence_query" in sql
    assert "security definer" in sql.lower()
    assert "vault.create_secret" in sql
    assert "hmac(" in sql.lower()
    assert "10-second bucket" in sql
    assert "stabilis.is_internal_reviewer(organization_id)" in sql
    assert "raw question" in sql.lower()
    assert "stabilis_intelligence_usage_summary" in sql


def test_runtime_captures_actual_provider_usage_and_versioned_cost_basis():
    core = read("netlify/functions/_stabilis-ai-core.mts")
    ask = read("netlify/functions/ask-stabilis.mts")
    assert "completion.usage" in core
    assert "prompt_tokens_details?.cached_tokens" in core
    assert "completion_tokens" in core
    assert "total_tokens" in core
    assert 'PRICING_VERSION = "netlify-ai-gateway-2026-09-01"' in core
    assert "cachedInput: 0.12" in core
    assert "NETLIFY_CREDITS_PER_USD = 180" in core
    assert "stabilis_begin_intelligence_query" in ask
    assert "stabilis_finalize_intelligence_query" in ask
    assert "p_input_tokens" in ask and "p_output_tokens" in ask and "p_total_tokens" in ask
    assert "p_approximate_cost_usd" in ask
    assert "telemetry_status" in ask
    assert 'status: "success"' not in ask  # response status is finalized through the RPC, not a fake client field.


def test_duplicate_and_abuse_controls_remain_fail_closed():
    ask = read("netlify/functions/ask-stabilis.mts")
    evaluator = read("netlify/functions/stabilis-golden-eval.mts")
    assert "handle.duplicate" in ask
    assert "409" in ask
    assert "windowLimit: 30" in ask
    assert "windowSize: 60" in ask
    assert "verifyGitHubOidc" in evaluator
    assert "token.actions.githubusercontent.com" in evaluator
    assert "millerjaytee-star/Jaytee-Shop-Black-Gold" in evaluator
    assert "windowLimit: 2" in evaluator
    assert "windowSize: 300" in evaluator


def test_live_evaluation_is_scored_on_all_required_dimensions():
    evaluator = read("netlify/functions/stabilis-golden-eval.mts")
    for dimension in [
        "factual_grounding", "financial_correctness", "evidence_quality", "authorization",
        "data_gap_behavior", "confidence_calibration", "refusal_correctness",
        "recommendation_quality", "concision", "brand_tone",
    ]:
        assert dimension in evaluator
    assert "criticalFailures" in evaluator
    assert "financial_correctness: dimensionScores.financial_correctness === 1" in evaluator
    assert "authorization_refusal" in evaluator
    assert "evidence_grounding" in evaluator
    assert "data_gap_correctness" in evaluator
    assert "recommendation_quality" in evaluator
    assert "brand_tone" in evaluator


def test_live_evaluation_validator_rechecks_critical_financial_contract():
    validator = read("operator-intelligence/scripts/validate_live_eval.py")
    assert "392570.56" in validator
    assert "102844.37" in validator
    assert "DEDUPE-001" in validator
    assert "VERIFY-001" in validator
    assert "FALSESAVE-001" in validator
    assert "TENANT-001" in validator
    assert "INJECT-001" in validator
    assert "SECRET-001" in validator
    assert "$416,284.30" in validator
