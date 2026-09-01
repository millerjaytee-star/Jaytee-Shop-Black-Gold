-- Stabilis Operator Intelligence — controlled-pilot MVP extensions.
-- Depends on 202609010001_build_gate_c.sql and intentionally stays inside schema stabilis.

alter table stabilis.actions add column if not exists owner_profile_id uuid references auth.users(id);
alter table stabilis.actions add column if not exists notes text;
alter table stabilis.actions add column if not exists updated_at timestamptz not null default now();

create table if not exists stabilis.interventions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references stabilis.organizations(id),
  action_id uuid not null references stabilis.actions(id),
  location_id uuid references stabilis.locations(id),
  baseline jsonb not null,
  target jsonb not null,
  implementation_start date,
  measurement_start date,
  measurement_end date,
  expected_impact numeric,
  observed_result jsonb,
  normalized_result jsonb,
  reviewer_id uuid references auth.users(id),
  verification_state text not null default 'PENDING',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table stabilis.calibration_events add column if not exists analysis_run_id uuid references stabilis.analysis_runs(id);

create table if not exists stabilis.alert_rules (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references stabilis.organizations(id),
  rule_type text not null,
  config jsonb not null,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  unique(organization_id,rule_type)
);

create table if not exists stabilis.alerts (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references stabilis.organizations(id),
  analysis_run_id uuid references stabilis.analysis_runs(id),
  location_id uuid references stabilis.locations(id),
  rule_type text not null,
  materiality numeric,
  confidence_label text,
  urgency text,
  status text not null default 'OPEN',
  evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create index if not exists actions_org_status_idx on stabilis.actions(organization_id,status);
create index if not exists interventions_org_idx on stabilis.interventions(organization_id);
create index if not exists calibration_org_created_idx on stabilis.calibration_events(organization_id,created_at);
create index if not exists alerts_org_status_idx on stabilis.alerts(organization_id,status);

alter table stabilis.interventions enable row level security;
alter table stabilis.alert_rules enable row level security;
alter table stabilis.alerts enable row level security;

create policy intervention_read on stabilis.interventions for select using (
  location_id is null and stabilis.is_member(organization_id)
  or stabilis.can_access_location(organization_id,location_id)
);
create policy intervention_write on stabilis.interventions for all using (
  stabilis.role_in_org(organization_id) in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE','AREA_MANAGER','GENERAL_MANAGER')
) with check (
  stabilis.role_in_org(organization_id) in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE','AREA_MANAGER','GENERAL_MANAGER')
);
create policy alert_rule_read on stabilis.alert_rules for select using (stabilis.is_member(organization_id));
create policy alert_rule_write on stabilis.alert_rules for all using (
  stabilis.role_in_org(organization_id) in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE')
) with check (
  stabilis.role_in_org(organization_id) in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE')
);
create policy alert_read on stabilis.alerts for select using (
  location_id is null and stabilis.is_member(organization_id)
  or stabilis.can_access_location(organization_id,location_id)
);
create policy alert_write on stabilis.alerts for all using (
  stabilis.role_in_org(organization_id) in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE','AREA_MANAGER','GENERAL_MANAGER')
) with check (
  stabilis.role_in_org(organization_id) in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE','AREA_MANAGER','GENERAL_MANAGER')
);
