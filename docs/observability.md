# Controlled-Pilot Observability

Stabilis monitors operational failures through the existing `processing_logs`, `system_events`, ingestion job state, validation/data-quality state, forecast runs, report runs, alerts and Supabase/Netlify platform logs.

Required pilot review surfaces:
- failed imports and ingestion jobs;
- validation and reconciliation failures;
- calculation / analysis-run failures;
- report-generation failures;
- login/auth failures through Supabase Auth logs;
- stale data sources / integrations;
- long-running or stuck jobs;
- forecast generation and accuracy state;
- system/security alerts.

Logging rule: do not duplicate raw sensitive financial file bodies into general application or product-analytics logs. Prefer safe IDs, state, event code, organization scope, timing and sanitized error messages.
