-- Stabilis Operator Intelligence — Full Platform + Command Center foundations
-- Idempotent repository source of truth for the live full-platform extensions.
create extension if not exists citext;

-- Existing full-platform domains. CREATE IF NOT EXISTS keeps this safe on the dedicated
-- Stabilis project where earlier live migrations may already have created these objects.
create table if not exists stabilis.organization_profiles (
  organization_id uuid primary key references stabilis.organizations(id) on delete cascade,
  legal_name text, industry text not null default 'restaurant', timezone text not null default 'America/New_York',
  currency_code text not null default 'USD', metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists stabilis.invitations (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  email citext not null, role stabilis.app_role not null, token_hash text not null unique,
  invited_by uuid references auth.users(id), expires_at timestamptz not null, accepted_at timestamptz, revoked_at timestamptz,
  created_at timestamptz not null default now()
);
create table if not exists stabilis.location_groups (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  name text not null, group_type text not null default 'CUSTOM', created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(organization_id,name)
);
create table if not exists stabilis.location_group_memberships (
  location_group_id uuid not null references stabilis.location_groups(id) on delete cascade,
  location_id uuid not null references stabilis.locations(id) on delete cascade, created_at timestamptz not null default now(),
  primary key(location_group_id,location_id)
);
create table if not exists stabilis.operating_targets (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  location_id uuid references stabilis.locations(id) on delete cascade, metric_name text not null, target_value numeric not null, unit text,
  effective_from date not null, effective_to date, source text not null default 'OPERATOR_APPROVED', confidence text not null default 'HIGH',
  methodology_version text not null default 'TARGET-v1', created_by uuid references auth.users(id), created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists stabilis.benchmarks (
  id uuid primary key default gen_random_uuid(), organization_id uuid references stabilis.organizations(id) on delete cascade,
  metric_name text not null, cohort_type text not null, cohort_definition jsonb not null default '{}'::jsonb,
  benchmark_value numeric not null, unit text, source_name text not null, source_url text, source_freshness timestamptz,
  effective_from date, effective_to date, confidence text not null default 'MEDIUM', external boolean not null default false,
  methodology_version text not null default 'BENCHMARK-v1', created_at timestamptz not null default now()
);
create table if not exists stabilis.data_sources (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  source_type text not null, provider text, name text not null, status text not null default 'ACTIVE', freshness_sla_hours int,
  last_success_at timestamptz, metadata jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists stabilis.integrations (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  data_source_id uuid references stabilis.data_sources(id) on delete cascade, provider text not null, status text not null default 'DISCONNECTED',
  external_account_ref text, credential_ref text, scopes jsonb not null default '[]'::jsonb, last_sync_at timestamptz, error_state jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists stabilis.import_batches (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  ingestion_job_id uuid references stabilis.ingestion_jobs(id) on delete set null, batch_type text not null, period_start date, period_end date,
  status text not null default 'UPLOADED', record_count int not null default 0, source_manifest jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
create table if not exists stabilis.column_mappings (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  import_batch_id uuid references stabilis.import_batches(id) on delete cascade, source_column text not null, canonical_field text not null,
  confidence numeric, status text not null default 'SUGGESTED', resolved_by uuid references auth.users(id), resolved_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists stabilis.validation_errors (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  import_batch_id uuid references stabilis.import_batches(id) on delete cascade, raw_file_id uuid references stabilis.raw_files(id) on delete cascade,
  location_id uuid references stabilis.locations(id) on delete set null, source_row int, field_name text, error_code text not null,
  severity text not null, message text not null, status text not null default 'OPEN', resolution jsonb, resolved_by uuid references auth.users(id),
  resolved_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists stabilis.data_quality_checks (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  import_batch_id uuid references stabilis.import_batches(id) on delete cascade, check_code text not null, check_version text not null,
  result text not null, score_delta numeric not null default 0, details jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);

create table if not exists stabilis.fact_sales (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  location_id uuid not null references stabilis.locations(id) on delete cascade, fiscal_period_id uuid references stabilis.fiscal_periods(id),
  business_date date not null, gross_sales numeric not null default 0, discounts numeric not null default 0, comps numeric not null default 0,
  refunds numeric not null default 0, net_sales numeric not null, transactions numeric, channel text, daypart text,
  source_file_id uuid references stabilis.raw_files(id), source_record_ref text, normalization_version text not null, created_at timestamptz not null default now()
);
create table if not exists stabilis.fact_labor (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  location_id uuid not null references stabilis.locations(id) on delete cascade, fiscal_period_id uuid references stabilis.fiscal_periods(id),
  business_date date not null, wages numeric not null default 0, payroll_taxes numeric not null default 0, benefits numeric not null default 0,
  other_burden numeric not null default 0, labor_cost numeric not null, productive_hours numeric, overtime_hours numeric, overtime_cost numeric,
  role_name text, daypart text, source_file_id uuid references stabilis.raw_files(id), source_record_ref text, normalization_version text not null,
  created_at timestamptz not null default now()
);
create table if not exists stabilis.fact_inventory (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  location_id uuid not null references stabilis.locations(id) on delete cascade, count_date date not null, category text,
  theoretical_value numeric, book_value numeric, physical_value numeric, variance_value numeric, waste_value numeric,
  source_file_id uuid references stabilis.raw_files(id), normalization_version text not null, created_at timestamptz not null default now()
);
create table if not exists stabilis.metric_definitions (
  id uuid primary key default gen_random_uuid(), metric_name text not null, version text not null, formula text not null, unit text,
  required_inputs jsonb not null default '[]'::jsonb, definition text, active boolean not null default true, created_at timestamptz not null default now(), unique(metric_name,version)
);
create table if not exists stabilis.score_definitions (
  id uuid primary key default gen_random_uuid(), score_name text not null, version text not null, weights jsonb not null, bands jsonb not null,
  minimum_coverage numeric, explanation text, active boolean not null default true, created_at timestamptz not null default now(), unique(score_name,version)
);

alter table stabilis.opportunities add column if not exists canonical_opportunity_id text;
alter table stabilis.opportunities add column if not exists opportunity_kind text not null default 'PRIMARY';
alter table stabilis.opportunities add column if not exists counted_in_rollup boolean not null default false;
alter table stabilis.opportunities add column if not exists monthly_estimate numeric;
alter table stabilis.opportunities add column if not exists priority_score numeric;
alter table stabilis.opportunities add column if not exists priority_class text;
create unique index if not exists opportunity_one_counted_canonical_idx on stabilis.opportunities(analysis_run_id,canonical_opportunity_id) where counted_in_rollup;
create or replace view stabilis.canonical_opportunity_rollup as
select analysis_run_id, organization_id,
       sum(base_estimate) as modeled_recoverable_opportunity,
       sum(coalesce(annualized_value,base_estimate)) as annualized_modeled_opportunity,
       count(*) as counted_opportunities
from stabilis.opportunities
where counted_in_rollup and opportunity_kind = 'PRIMARY'
group by analysis_run_id,organization_id;

create table if not exists stabilis.opportunity_evidence (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  opportunity_id uuid not null references stabilis.opportunities(id) on delete cascade, finding_id uuid references stabilis.findings(id) on delete set null,
  metric_id uuid references stabilis.metrics(id) on delete set null, source_file_id uuid references stabilis.raw_files(id) on delete set null,
  evidence_role text not null default 'SUPPORTING', evidence jsonb not null, created_at timestamptz not null default now()
);
create table if not exists stabilis.opportunity_scenarios (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  opportunity_id uuid not null references stabilis.opportunities(id) on delete cascade, scenario_name text not null, estimated_amount numeric,
  assumptions jsonb not null, calculation_version text not null, created_at timestamptz not null default now(), unique(opportunity_id,scenario_name,calculation_version)
);
create table if not exists stabilis.recommendation_versions (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  recommendation_id uuid not null references stabilis.recommendations(id) on delete cascade, version int not null, body jsonb not null,
  model_provider text, model_name text, model_version text, generated_by text not null, created_by uuid references auth.users(id),
  created_at timestamptz not null default now(), unique(recommendation_id,version)
);
create table if not exists stabilis.confidence_assessments (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  analysis_run_id uuid references stabilis.analysis_runs(id) on delete cascade, entity_type text not null, entity_id uuid not null,
  confidence_label text not null, confidence_score numeric, input_quality numeric, calculation_validity numeric, benchmark_quality numeric,
  causal_certainty numeric, rationale jsonb not null, methodology_version text not null, created_at timestamptz not null default now()
);

create table if not exists stabilis.action_updates (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  action_id uuid not null references stabilis.actions(id) on delete cascade, status text, note text, blocker text,
  changed_by uuid references auth.users(id), created_at timestamptz not null default now()
);
create table if not exists stabilis.observed_results (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  action_id uuid references stabilis.actions(id) on delete set null, intervention_id uuid references stabilis.interventions(id) on delete set null,
  location_id uuid references stabilis.locations(id) on delete set null, measurement_start date not null, measurement_end date not null,
  baseline jsonb not null, observed jsonb not null, financial_change numeric, attribution_status text not null default 'UNVERIFIED',
  created_at timestamptz not null default now()
);
create table if not exists stabilis.verified_values (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  observed_result_id uuid not null references stabilis.observed_results(id) on delete cascade, opportunity_id uuid references stabilis.opportunities(id) on delete set null,
  action_id uuid references stabilis.actions(id) on delete set null, verified_amount numeric not null, verification_method text not null,
  verification_status text not null default 'PENDING', verified_by uuid references auth.users(id), verified_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists stabilis.verification_reviews (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  verified_value_id uuid not null references stabilis.verified_values(id) on delete cascade, decision text not null, rationale text,
  reviewer_id uuid not null references auth.users(id), created_at timestamptz not null default now()
);
create table if not exists stabilis.report_runs (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  analysis_run_id uuid references stabilis.analysis_runs(id) on delete set null, report_type text not null, status text not null default 'QUEUED',
  requested_by uuid references auth.users(id), started_at timestamptz, completed_at timestamptz, error_code text, safe_error_message text,
  created_at timestamptz not null default now()
);
create table if not exists stabilis.report_versions (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  report_run_id uuid not null references stabilis.report_runs(id) on delete cascade, version int not null, content_hash text not null,
  release_status text not null default 'DRAFT', generated_by text not null, model_provider text, model_name text,
  approved_by uuid references auth.users(id), approved_at timestamptz, created_at timestamptz not null default now(), unique(report_run_id,version)
);
create table if not exists stabilis.generated_documents (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  report_version_id uuid not null references stabilis.report_versions(id) on delete cascade, storage_bucket text not null default 'stabilis-reports',
  storage_path text not null, mime_type text not null, size_bytes bigint, sha256 text not null, created_at timestamptz not null default now(),
  unique(organization_id,storage_path)
);
create table if not exists stabilis.processing_logs (
  id uuid primary key default gen_random_uuid(), organization_id uuid references stabilis.organizations(id) on delete cascade,
  process_type text not null, process_id uuid, severity text not null, event_code text not null, safe_message text not null,
  safe_metadata jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);
create table if not exists stabilis.system_events (
  id uuid primary key default gen_random_uuid(), organization_id uuid references stabilis.organizations(id) on delete cascade,
  event_type text not null, actor_id uuid references auth.users(id), entity_type text, entity_id uuid,
  safe_payload jsonb not null default '{}'::jsonb, created_at timestamptz not null default now()
);
create table if not exists stabilis.feature_flags (
  id uuid primary key default gen_random_uuid(), organization_id uuid references stabilis.organizations(id) on delete cascade,
  flag_key text not null, enabled boolean not null default false, configuration jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(organization_id,flag_key)
);

-- Command Center forecast foundation. These tables persist versioned inputs, outputs and measured accuracy.
create table if not exists stabilis.forecast_models (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  name text not null, model_type text not null default 'DETERMINISTIC', version text not null, status text not null default 'ACTIVE',
  methodology jsonb not null default '{}'::jsonb, created_by uuid references auth.users(id), created_at timestamptz not null default now(),
  unique(organization_id,name,version)
);
create table if not exists stabilis.forecast_runs (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  model_id uuid references stabilis.forecast_models(id) on delete restrict, period_start date not null, period_end date not null,
  generated_at timestamptz not null default now(), status text not null default 'COMPLETED', confidence_score numeric,
  input_manifest jsonb not null default '{}'::jsonb, methodology_version text not null, created_by uuid references auth.users(id)
);
create table if not exists stabilis.forecast_inputs (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  forecast_run_id uuid not null references stabilis.forecast_runs(id) on delete cascade, location_id uuid references stabilis.locations(id) on delete cascade,
  input_type text not null, period_date date, value numeric, payload jsonb not null default '{}'::jsonb,
  source_file_id uuid references stabilis.raw_files(id) on delete set null, created_at timestamptz not null default now()
);
create table if not exists stabilis.forecast_values (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  forecast_run_id uuid not null references stabilis.forecast_runs(id) on delete cascade, location_id uuid references stabilis.locations(id) on delete cascade,
  forecast_date date not null, metric_name text not null, forecast_value numeric not null, lower_bound numeric, upper_bound numeric,
  confidence_score numeric, unit text, created_at timestamptz not null default now(),
  unique(forecast_run_id,location_id,forecast_date,metric_name)
);
create table if not exists stabilis.forecast_accuracy (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  forecast_run_id uuid not null references stabilis.forecast_runs(id) on delete cascade, location_id uuid references stabilis.locations(id) on delete cascade,
  metric_name text not null, measured_date date not null, forecast_value numeric not null, actual_value numeric not null,
  absolute_error numeric, absolute_percentage_error numeric, bias numeric, methodology_version text not null,
  created_at timestamptz not null default now(), unique(forecast_run_id,location_id,metric_name,measured_date)
);

-- User-specific command-center preferences. Organization isolation is still enforced; these never contain canonical financial truth.
create table if not exists stabilis.user_preferences (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  profile_id uuid not null references stabilis.profiles(id) on delete cascade, preference_key text not null, preference_value jsonb not null,
  created_at timestamptz not null default now(), updated_at timestamptz not null default now(), unique(organization_id,profile_id,preference_key)
);
create table if not exists stabilis.widget_preferences (
  id uuid primary key default gen_random_uuid(), organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  profile_id uuid not null references stabilis.profiles(id) on delete cascade, widget_key text not null, position int, width int, enabled boolean not null default true,
  configuration jsonb not null default '{}'::jsonb, created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
  unique(organization_id,profile_id,widget_key)
);

create index if not exists forecast_runs_org_period_idx on stabilis.forecast_runs(organization_id,period_start,period_end);
create index if not exists forecast_values_org_loc_date_idx on stabilis.forecast_values(organization_id,location_id,forecast_date);
create index if not exists forecast_accuracy_org_loc_date_idx on stabilis.forecast_accuracy(organization_id,location_id,measured_date);

alter table stabilis.forecast_models enable row level security;
alter table stabilis.forecast_runs enable row level security;
alter table stabilis.forecast_inputs enable row level security;
alter table stabilis.forecast_values enable row level security;
alter table stabilis.forecast_accuracy enable row level security;
alter table stabilis.user_preferences enable row level security;
alter table stabilis.widget_preferences enable row level security;

drop policy if exists forecast_models_read on stabilis.forecast_models;
create policy forecast_models_read on stabilis.forecast_models for select to authenticated using (stabilis.is_member(organization_id));
drop policy if exists forecast_models_write on stabilis.forecast_models;
create policy forecast_models_write on stabilis.forecast_models for all to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));

drop policy if exists forecast_runs_read on stabilis.forecast_runs;
create policy forecast_runs_read on stabilis.forecast_runs for select to authenticated using (stabilis.is_member(organization_id));
drop policy if exists forecast_runs_write on stabilis.forecast_runs;
create policy forecast_runs_write on stabilis.forecast_runs for all to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));

drop policy if exists forecast_inputs_read on stabilis.forecast_inputs;
create policy forecast_inputs_read on stabilis.forecast_inputs for select to authenticated using ((location_id is null and stabilis.is_member(organization_id)) or stabilis.can_access_location(organization_id,location_id));
drop policy if exists forecast_inputs_write on stabilis.forecast_inputs;
create policy forecast_inputs_write on stabilis.forecast_inputs for all to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));

drop policy if exists forecast_values_read on stabilis.forecast_values;
create policy forecast_values_read on stabilis.forecast_values for select to authenticated using ((location_id is null and stabilis.is_member(organization_id)) or stabilis.can_access_location(organization_id,location_id));
drop policy if exists forecast_values_write on stabilis.forecast_values;
create policy forecast_values_write on stabilis.forecast_values for all to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));

drop policy if exists forecast_accuracy_read on stabilis.forecast_accuracy;
create policy forecast_accuracy_read on stabilis.forecast_accuracy for select to authenticated using ((location_id is null and stabilis.is_member(organization_id)) or stabilis.can_access_location(organization_id,location_id));
drop policy if exists forecast_accuracy_write on stabilis.forecast_accuracy;
create policy forecast_accuracy_write on stabilis.forecast_accuracy for all to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));

drop policy if exists user_preferences_self on stabilis.user_preferences;
create policy user_preferences_self on stabilis.user_preferences for all to authenticated
using (profile_id = (select auth.uid()) and stabilis.is_member(organization_id))
with check (profile_id = (select auth.uid()) and stabilis.is_member(organization_id));
drop policy if exists widget_preferences_self on stabilis.widget_preferences;
create policy widget_preferences_self on stabilis.widget_preferences for all to authenticated
using (profile_id = (select auth.uid()) and stabilis.is_member(organization_id))
with check (profile_id = (select auth.uid()) and stabilis.is_member(organization_id));

grant select, insert, update on stabilis.forecast_models, stabilis.forecast_runs, stabilis.forecast_inputs, stabilis.forecast_values, stabilis.forecast_accuracy, stabilis.user_preferences, stabilis.widget_preferences to authenticated;
grant all on stabilis.forecast_models, stabilis.forecast_runs, stabilis.forecast_inputs, stabilis.forecast_values, stabilis.forecast_accuracy, stabilis.user_preferences, stabilis.widget_preferences to service_role;

-- Storage contract remains private. Existing bucket migrations create these buckets.
-- ('stabilis-reports','stabilis-reports',false)
-- ('stabilis-evidence','stabilis-evidence',false)

comment on view stabilis.canonical_opportunity_rollup is 'Canonical opportunity rollup. Count PRIMARY opportunities only. Supporting HHR-07 overtime evidence is not counted twice.';
