-- Ask Stabilis production intelligence layer.
-- Financial truth remains deterministic; this layer exposes only tenant-authorized structured context.

create table if not exists stabilis.intelligence_queries (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  profile_id uuid not null references stabilis.profiles(id) on delete cascade,
  location_scope jsonb not null default '[]'::jsonb,
  query_category text not null,
  model_provider text not null,
  model_name text not null,
  model_version text,
  response_status text not null,
  evidence_refs jsonb not null default '[]'::jsonb,
  latency_ms integer,
  error_code text,
  created_at timestamptz not null default now()
);

create table if not exists stabilis.intelligence_query_feedback (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  query_id uuid not null references stabilis.intelligence_queries(id) on delete cascade,
  profile_id uuid not null references stabilis.profiles(id) on delete cascade,
  rating text not null check (rating in ('HELPFUL','NOT_HELPFUL')),
  reason text check (reason in ('INCORRECT','MISSING_CONTEXT','TOO_VAGUE','GOOD_RECOMMENDATION','OTHER')),
  comment text,
  created_at timestamptz not null default now(),
  unique(query_id,profile_id)
);

create index if not exists intelligence_queries_org_created_idx on stabilis.intelligence_queries(organization_id,created_at desc);
create index if not exists intelligence_queries_profile_created_idx on stabilis.intelligence_queries(profile_id,created_at desc);
create index if not exists intelligence_feedback_org_created_idx on stabilis.intelligence_query_feedback(organization_id,created_at desc);

alter table stabilis.intelligence_queries enable row level security;
alter table stabilis.intelligence_query_feedback enable row level security;

drop policy if exists intelligence_queries_read on stabilis.intelligence_queries;
create policy intelligence_queries_read on stabilis.intelligence_queries for select to authenticated
using (profile_id=(select auth.uid()) or stabilis.is_internal_reviewer(organization_id));

drop policy if exists intelligence_feedback_read on stabilis.intelligence_query_feedback;
create policy intelligence_feedback_read on stabilis.intelligence_query_feedback for select to authenticated
using (profile_id=(select auth.uid()) or stabilis.is_internal_reviewer(organization_id));

revoke all on stabilis.intelligence_queries, stabilis.intelligence_query_feedback from anon;
grant select on stabilis.intelligence_queries, stabilis.intelligence_query_feedback to authenticated;

create or replace function public.stabilis_intelligence_context(p_organization_id uuid,p_location_id uuid default null)
returns jsonb
language plpgsql
stable
security invoker
set search_path=public,stabilis,pg_temp
as $$
declare
  v_workspace jsonb;
  v_run uuid;
  v_metrics jsonb;
  v_findings jsonb;
  v_verified jsonb;
  v_observed jsonb;
begin
  if auth.uid() is null or not stabilis.is_member(p_organization_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  if p_location_id is not null and not stabilis.can_access_location(p_organization_id,p_location_id) then
    raise exception 'location not authorized' using errcode='42501';
  end if;

  v_workspace := public.stabilis_workspace_payload(p_organization_id,p_location_id);
  v_run := nullif(v_workspace #>> '{context,latest_analysis_run_id}','')::uuid;

  select coalesce(jsonb_agg(to_jsonb(x) order by x.period desc,x.metric_name),'[]'::jsonb) into v_metrics
  from (
    select m.id,m.location_id,l.code location_code,m.period,m.metric_name,m.value,m.unit,m.formula_version,m.lineage,m.created_at
    from stabilis.metrics m left join stabilis.locations l on l.id=m.location_id
    where m.organization_id=p_organization_id
      and (v_run is null or m.analysis_run_id=v_run)
      and ((m.location_id is null and p_location_id is null) or
        (m.location_id is not null and stabilis.can_access_location(p_organization_id,m.location_id)
          and (p_location_id is null or m.location_id=p_location_id)))
    order by m.period desc,m.metric_name limit 120
  ) x;

  select coalesce(jsonb_agg(to_jsonb(x) order by x.created_at desc),'[]'::jsonb) into v_findings
  from (
    select f.id,f.location_id,l.code location_code,f.period,f.category,f.metric,f.current_value,f.benchmark_value,f.variance,
      f.benchmark_source,f.severity,f.materiality,f.confidence_label,f.confidence_score,f.status,f.root_cause_status,f.evidence,f.created_at
    from stabilis.findings f left join stabilis.locations l on l.id=f.location_id
    where f.organization_id=p_organization_id
      and (v_run is null or f.analysis_run_id=v_run)
      and ((f.location_id is null and p_location_id is null) or
        (f.location_id is not null and stabilis.can_access_location(p_organization_id,f.location_id)
          and (p_location_id is null or f.location_id=p_location_id)))
    order by f.created_at desc limit 60
  ) x;

  select coalesce(jsonb_agg(to_jsonb(x) order by x.verified_at desc nulls last,x.created_at desc),'[]'::jsonb) into v_verified
  from (
    select vv.id,vv.opportunity_id,vv.action_id,vv.verified_amount,vv.verification_method,vv.verification_status,vv.verified_at,vv.created_at
    from stabilis.verified_values vv
    where vv.organization_id=p_organization_id
      and (p_location_id is null
        or exists(select 1 from stabilis.actions a where a.id=vv.action_id and a.organization_id=p_organization_id and a.location_id=p_location_id)
        or exists(select 1 from stabilis.opportunities o where o.id=vv.opportunity_id and o.organization_id=p_organization_id and o.location_id=p_location_id))
    order by vv.verified_at desc nulls last,vv.created_at desc limit 40
  ) x;

  select coalesce(jsonb_agg(to_jsonb(x) order by x.created_at desc),'[]'::jsonb) into v_observed
  from (
    select r.id,r.action_id,r.intervention_id,r.location_id,l.code location_code,r.measurement_start,r.measurement_end,
      r.baseline,r.observed,r.financial_change,r.attribution_status,r.created_at
    from stabilis.observed_results r left join stabilis.locations l on l.id=r.location_id
    where r.organization_id=p_organization_id
      and (p_location_id is null or r.location_id=p_location_id)
      and (r.location_id is null or stabilis.can_access_location(p_organization_id,r.location_id))
    order by r.created_at desc limit 40
  ) x;

  return jsonb_build_object(
    'workspace',v_workspace,'metrics',v_metrics,'findings',v_findings,'observed_results',v_observed,'verified_values',v_verified,
    'financial_stage_definitions',jsonb_build_object(
      'modeled_opportunity','Potential recoverable opportunity calculated by Stabilis; not savings.',
      'action_underway','An approved operating intervention is being executed.',
      'observed_improvement','Measured movement after intervention; attribution not yet verified.',
      'verified_financial_impact','Reviewer-approved financial attribution supported by evidence.'
    )
  );
end $$;

revoke all on function public.stabilis_intelligence_context(uuid,uuid) from public,anon;
grant execute on function public.stabilis_intelligence_context(uuid,uuid) to authenticated;

create or replace function public.stabilis_log_intelligence_query(
  p_organization_id uuid,p_location_scope jsonb,p_query_category text,p_model_provider text,p_model_name text,p_model_version text,
  p_response_status text,p_evidence_refs jsonb default '[]'::jsonb,p_latency_ms integer default null,p_error_code text default null
) returns uuid
language plpgsql
set search_path=public,stabilis,pg_temp
as $$
declare v_id uuid;
begin
  if auth.uid() is null or not stabilis.is_member(p_organization_id) then raise exception 'not authorized' using errcode='42501'; end if;
  insert into stabilis.intelligence_queries(organization_id,profile_id,location_scope,query_category,model_provider,model_name,model_version,response_status,evidence_refs,latency_ms,error_code)
  values(p_organization_id,auth.uid(),coalesce(p_location_scope,'[]'::jsonb),left(coalesce(p_query_category,'other'),80),left(coalesce(p_model_provider,'unknown'),80),left(coalesce(p_model_name,'unknown'),120),left(p_model_version,120),left(coalesce(p_response_status,'unknown'),40),coalesce(p_evidence_refs,'[]'::jsonb),p_latency_ms,left(p_error_code,120))
  returning id into v_id;
  return v_id;
end $$;
revoke all on function public.stabilis_log_intelligence_query(uuid,jsonb,text,text,text,text,text,jsonb,integer,text) from public,anon;
grant execute on function public.stabilis_log_intelligence_query(uuid,jsonb,text,text,text,text,text,jsonb,integer,text) to authenticated;

create or replace function public.stabilis_submit_intelligence_feedback(p_organization_id uuid,p_query_id uuid,p_rating text,p_reason text default null,p_comment text default null)
returns uuid
language plpgsql
set search_path=public,stabilis,pg_temp
as $$
declare v_id uuid;
begin
  if auth.uid() is null or not stabilis.is_member(p_organization_id) then raise exception 'not authorized' using errcode='42501'; end if;
  if not exists(select 1 from stabilis.intelligence_queries q where q.id=p_query_id and q.organization_id=p_organization_id and q.profile_id=auth.uid()) then
    raise exception 'query not authorized' using errcode='42501';
  end if;
  insert into stabilis.intelligence_query_feedback(organization_id,query_id,profile_id,rating,reason,comment)
  values(p_organization_id,p_query_id,auth.uid(),upper(p_rating),nullif(upper(coalesce(p_reason,'')),''),left(p_comment,2000))
  on conflict(query_id,profile_id) do update set rating=excluded.rating,reason=excluded.reason,comment=excluded.comment,created_at=now()
  returning id into v_id;
  return v_id;
end $$;
revoke all on function public.stabilis_submit_intelligence_feedback(uuid,uuid,text,text,text) from public,anon;
grant execute on function public.stabilis_submit_intelligence_feedback(uuid,uuid,text,text,text) to authenticated;

comment on function public.stabilis_intelligence_context(uuid,uuid) is 'Tenant- and location-authorized compact context for Ask Stabilis. Financial truth remains deterministic and this function exposes no service credentials.';
