# Stabilis Production Migration Ledger

This ledger maps the dedicated Stabilis Supabase production history to the repository migration artifacts used to reproduce the current schema. It exists because the full-platform release was applied to production in smaller audited chunks while the repository preserves the same resulting schema in consolidated migration files.

## Dedicated production project

Project ref: `vpunfmwklwjefvchvmpn`

## Persistent product migrations

| Live Supabase migration | Repository source / disposition |
| --- | --- |
| `build_gate_c` | Historical Build Gate C foundation. Its durable schema is the prerequisite baseline for the later repository migrations and is retained in Supabase migration audit history. |
| `mvp_extensions` | `operator-intelligence/supabase/migrations/202609010002_mvp_extensions.sql` |
| `full_platform_identity_ingestion` | Consolidated into `operator-intelligence/supabase/migrations/202609010003_full_platform_schema.sql` |
| `full_platform_facts_intelligence` | Consolidated into `operator-intelligence/supabase/migrations/202609010003_full_platform_schema.sql` |
| `full_platform_execution_reporting` | Consolidated into `operator-intelligence/supabase/migrations/202609010003_full_platform_schema.sql` |
| `full_platform_rls_storage_seed` | Consolidated into `operator-intelligence/supabase/migrations/202609010003_full_platform_schema.sql` |
| `security_performance_hardening` | Durable RLS/index hardening represented by the consolidated full-platform schema plus the later explicit policy-hardening migrations. |
| `performance_cleanup` | Durable cleanup represented by the current consolidated schema/index state. |
| `command_center_forecast_foundation` | Forecast foundation represented by the full-platform schema and forecast hardening migration. |
| `forecast_policy_performance_hardening` | `operator-intelligence/supabase/migrations/202609010004_forecast_policy_performance_hardening.sql` |
| `public_customer_context_views` | `operator-intelligence/supabase/migrations/202609010004_public_customer_context.sql` |
| `controlled_pilot_product_layer` | `operator-intelligence/supabase/migrations/20260901164000_controlled_pilot_product_layer.sql` |
| `insight_feedback_rpc` | `operator-intelligence/supabase/migrations/20260901164100_insight_feedback_rpc.sql` |
| `controlled_pilot_performance_hardening` | `operator-intelligence/supabase/migrations/20260901193000_controlled_pilot_performance_hardening.sql` |

## Ephemeral release-verification migrations

The following migrations are intentionally retained in Supabase's audit history but do not represent hidden product schema. They were used only for production-equivalent release smoke testing and were subsequently removed/reversed:

- `enable_http_release_smoke` — temporarily enabled an HTTP smoke-test capability.
- `release_smoke_seed_helpers` — temporary QA seed helpers.
- `release_smoke_seed_profile_upsert` — temporary QA profile helper.
- `remove_release_smoke_seed_helpers` — removed the temporary QA helpers.
- `remove_temporary_http_smoke_extension` — removed the temporary HTTP smoke capability.

The final production state therefore does **not** depend on those temporary helpers or the temporary HTTP extension.

## Consistency rule

Production schema changes must be made through a tracked Supabase migration and, when durable, represented in this repository. Temporary release-test migrations must be explicitly paired with cleanup/removal and documented here. This ledger is the reconciliation record between production's fine-grained audit history and the repository's consolidated reproducible migration set.
