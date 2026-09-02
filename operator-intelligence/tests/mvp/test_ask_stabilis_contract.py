from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_ask_stabilis_is_server_side_and_authenticated():
    fn = read("netlify/functions/ask-stabilis.mts")
    core = read("netlify/functions/_stabilis-ai-core.mts")
    assert 'path: "/api/ask-stabilis"' in fn
    assert 'req.headers.get("authorization")' in fn
    assert 'supabase("/auth/v1/user"' in fn
    assert 'stabilis_intelligence_context' in fn
    assert 'runAskStabilisModel' in fn
    assert 'import OpenAI from "openai"' in core
    assert 'new OpenAI()' in core
    assert 'chat.completions.create' in core
    assert 'process.env.OPENAI_BASE_URL' in fn
    assert 'service_role' not in fn.lower()


def test_ask_stabilis_financial_truth_guards_are_explicit():
    fn = read("netlify/functions/ask-stabilis.mts")
    core = read("netlify/functions/_stabilis-ai-core.mts")
    combined = fn + core
    for contract in [
        "Financial truth is already calculated",
        "Never call modeled opportunity savings",
        "Supporting evidence does not add",
        "Not enough data",
        "hasInventedDollar",
        "guarded_financial_output",
    ]:
        assert contract in combined
    assert "No verified savings have been established yet" in fn


def test_ask_stabilis_prompt_injection_and_failure_states_exist():
    fn = read("netlify/functions/ask-stabilis.mts")
    core = read("netlify/functions/_stabilis-ai-core.mts")
    assert "isInjectionAttempt" in fn
    assert "PROMPT_INJECTION" in fn
    assert "Stabilis Intelligence is temporarily unavailable" in fn
    assert "AbortController" in core
    assert "OUTPUT_VALIDATION" in fn


def test_ai_gateway_health_probe_uses_supported_sdk_and_rate_limit():
    fn = read("netlify/functions/stabilis-ai-health.mts")
    package = read("package.json")
    assert 'import OpenAI from "openai"' in fn
    assert 'new OpenAI()' in fn
    assert 'chat.completions.create' in fn
    assert 'process.env.OPENAI_BASE_URL' in fn
    assert 'STABILIS_AI_HEALTH_TOKEN' in fn
    assert 'rateLimit' in fn
    assert 'windowLimit: 5' in fn
    assert 'aggregateBy: ["ip", "domain"]' in fn
    assert 'No customer data is included.' in fn
    assert '"openai": "7.8.0"' in package


def test_ask_stabilis_has_reasonable_abuse_guardrail():
    fn = read("netlify/functions/ask-stabilis.mts")
    assert 'rateLimit' in fn
    assert 'windowLimit: 30' in fn
    assert 'windowSize: 60' in fn
    assert 'handle.duplicate' in fn
    assert '409' in fn


def test_preview_qa_ignores_only_navigation_aborts_not_real_asset_failures():
    qa = read("operator-intelligence/scripts/release_preview_qa.py")
    assert "ignorable_navigation_abort" in qa
    assert "net::ERR_ABORTED" in qa
    assert 'page.on("requestfailed", capture_request_failure)' in qa
    assert "resp.status >= 400" in qa
    assert 'resp.request.resource_type in {"script", "stylesheet", "image", "font"}' in qa


def test_ask_stabilis_client_has_loading_retry_feedback_and_scope():
    app = read("app.html")
    client = read("assets/ask-stabilis.js")
    assert '/assets/ask-stabilis.js' in app
    assert '/api/ask-stabilis' in client
    assert 'orgSelect' in client and 'locationSelect' in client
    assert 'Ask Stabilis is working' in client
    assert 'askRetry' in client
    assert 'HELPFUL' in client and 'NOT_HELPFUL' in client
    assert 'Modeled Opportunity, Action Underway, Observed Improvement, and Verified Financial Impact are separate stages' in client


def test_ask_stabilis_database_migrations_are_versioned():
    base = read("operator-intelligence/supabase/migrations/20260901221000_ask_stabilis_intelligence.sql")
    hardening = read("operator-intelligence/supabase/migrations/20260902003000_ask_stabilis_telemetry_hardening.sql")
    assert "stabilis.intelligence_queries" in base
    assert "stabilis.intelligence_query_feedback" in base
    assert "public.stabilis_intelligence_context" in base
    assert "public.stabilis_log_intelligence_query" in base
    assert "enable row level security" in base.lower()
    assert "public.stabilis_begin_intelligence_query" in hardening
    assert "public.stabilis_finalize_intelligence_query" in hardening
    assert "public.stabilis_submit_intelligence_feedback" in hardening
    assert "security definer" in hardening.lower()
