-- Weekly labor reviews. Apply to a controlled Stabilis staging environment before rollout.
-- Memberships, role_in_org and can_access_location come from the existing Stabilis foundation.
begin;

-- The historical tenant foundation is not fully tracked in Git. Confirm the
-- persisted membership/location mapping used by the existing reference store.
-- Fail atomically on a different foundation, before creating customer objects.
do $$
begin
  if to_regclass('stabilis.membership_locations') is null then
    raise exception 'Verify the staging location-grant relation against can_access_location before applying the labor migration';
  end if;
end $$;

create table stabilis.labor_review_assignees (
  organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  location_id uuid not null references stabilis.locations(id) on delete cascade,
  profile_id uuid not null references stabilis.profiles(id) on delete cascade,
  display_name text not null,
  primary key (organization_id,location_id,profile_id)
);

create table stabilis.weekly_labor_reviews (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references stabilis.organizations(id) on delete cascade,
  location_id uuid not null references stabilis.locations(id) on delete cascade,
  week_start date not null,
  version integer not null default 1,
  status text not null default 'draft' check
    (status in ('draft','released','assigned','accepted','change_requested','evidence_submitted','compared','verified')),
  inputs jsonb not null,
  metrics jsonb not null,
  source text not null,
  action jsonb,
  followup jsonb,
  verification jsonb,
  history jsonb not null default '[]',
  updated_at timestamptz not null default now(),
  unique (organization_id, location_id, week_start)
);

-- One accepted financial credit per location/comparison week in this labor workflow.
create unique index weekly_labor_verified_period on stabilis.weekly_labor_reviews
  (organization_id, location_id, (followup->>'week_start'))
  where status = 'verified';

-- Preserve exact request and prior state for retries, audit and corrections.
create table stabilis.weekly_labor_audit (
  review_id uuid not null references stabilis.weekly_labor_reviews(id) on delete cascade,
  version integer not null,
  actor_id uuid not null,
  operation text not null,
  payload jsonb not null,
  previous_state jsonb,
  created_at timestamptz not null default now(),
  primary key (review_id,version)
);

alter table stabilis.labor_review_assignees enable row level security;
alter table stabilis.weekly_labor_reviews enable row level security;
alter table stabilis.weekly_labor_audit enable row level security;
-- No table grants or write policies. The RPCs are the only customer access paths.
revoke all on stabilis.weekly_labor_reviews, stabilis.labor_review_assignees,
  stabilis.weekly_labor_audit from public, anon, authenticated;

create function stabilis.labor_metrics(p jsonb) returns jsonb
language plpgsql immutable set search_path = '' as $$
declare
  k text; value jsonb;
  forecast numeric; sales numeric; target numeric; planned numeric; paid numeric;
  hours_planned numeric; hours_paid numeric;
begin
  if jsonb_typeof(p) is distinct from 'object' then raise exception 'Supply mapped week inputs'; end if;
  for k,value in select * from jsonb_each(p) loop
    if k not in ('forecast_sales','actual_sales','target_pct','scheduled_hours','actual_hours','scheduled_cost','actual_cost') then
      raise exception 'Unknown labor field: %', k;
    end if;
    if value = 'null'::jsonb then continue; end if;
    if jsonb_typeof(value) <> 'number' then raise exception 'Expected a numeric value for %', k; end if;
    if (p->>k)::numeric < 0 or (p->>k)::numeric > 1000000000000 then raise exception 'Out-of-range value for %', k; end if;
  end loop;
  if not exists(select 1 from jsonb_each(p) j where j.value <> 'null'::jsonb) then
    raise exception 'At least one measured input is required';
  end if;
  forecast := (p->>'forecast_sales')::numeric; sales := (p->>'actual_sales')::numeric;
  target := (p->>'target_pct')::numeric / 100;
  if target > 1 then raise exception 'Target must be between 0 and 100 percent'; end if;
  planned := (p->>'scheduled_cost')::numeric; paid := (p->>'actual_cost')::numeric;
  hours_planned := (p->>'scheduled_hours')::numeric; hours_paid := (p->>'actual_hours')::numeric;
  return jsonb_build_object(
    'actual_pct',round(100 * paid / nullif(sales,0),2),
    'points_over',round(100 * (paid / nullif(sales,0) - target),2),
    'hours_over',round(hours_paid-hours_planned,2),
    'schedule_effect',round(planned-target*forecast,2),
    'sales_effect',round(target*(forecast-sales),2),
    'payroll_effect',round(paid-planned,2),
    'total_over',round(paid-target*sales,2)
  );
end $$;

create function stabilis.labor_required_text(p jsonb,k text) returns text
language plpgsql immutable set search_path = '' as $$
declare v text := trim(p->>k);
begin
  if jsonb_typeof(p->k) is distinct from 'string' or nullif(v,'') is null or length(v)>2000 then
    raise exception 'Supply a valid % (up to 2,000 characters)', k;
  end if;
  return v;
end $$;

create function stabilis.labor_date(p jsonb,k text) returns date
language plpgsql immutable set search_path = '' as $$
declare v text := stabilis.labor_required_text(p,k);
begin
  if v !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'Supply % in YYYY-MM-DD format', k; end if;
  return v::date;
end $$;

create function stabilis.labor_closed_week(p jsonb, p_location uuid) returns date
language plpgsql stable set search_path = '' as $$
declare
  week_start date := stabilis.labor_date(p,'week_start');
  local_today date;
begin
  select (now() at time zone coalesce(nullif(l.timezone,''),'UTC'))::date
    into strict local_today from stabilis.locations l where l.id=p_location;
  if week_start+7>local_today then raise exception 'Choose a completed fiscal week for this location'; end if;
  return week_start;
end $$;

create function stabilis.labor_scope_role(org uuid, loc uuid) returns text
language plpgsql stable set search_path = '' as $$
declare r text := stabilis.role_in_org(org)::text;
begin
  if auth.uid() is null or r is null or loc is null
     or not exists (select 1 from stabilis.locations l where l.id=loc and l.organization_id=org)
     or not coalesce(stabilis.can_access_location(org,loc),false) then
    raise exception 'Location unavailable' using errcode='42501';
  end if;
  return r;
end $$;

create function public.stabilis_enroll_labor_assignee(p_organization_id uuid,p_location_id uuid,p_name text)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if stabilis.labor_scope_role(p_organization_id,p_location_id) <> 'GENERAL_MANAGER' then
    raise exception 'Location GM access required' using errcode='42501';
  end if;
  if nullif(trim(p_name),'') is null or length(trim(p_name))>120 then raise exception 'Supply a display name'; end if;
  insert into stabilis.labor_review_assignees values (p_organization_id,p_location_id,auth.uid(),trim(p_name))
  on conflict (organization_id,location_id,profile_id) do update set display_name=excluded.display_name;
end $$;

create function public.stabilis_labor_assignees(p_organization_id uuid,p_location_id uuid)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
begin
  perform stabilis.labor_scope_role(p_organization_id,p_location_id);
  return (select coalesce(jsonb_agg(jsonb_build_object('id',a.profile_id,'name',a.display_name) order by a.display_name),'[]'::jsonb)
    from stabilis.labor_review_assignees a join stabilis.memberships m
      on m.organization_id=a.organization_id and m.profile_id=a.profile_id and m.status='ACTIVE' and m.role::text='GENERAL_MANAGER'
    join stabilis.membership_locations g on g.membership_id=m.id and g.location_id=a.location_id
    where a.organization_id=p_organization_id and a.location_id=p_location_id);
end $$;

create function public.stabilis_labor_reviews(p_organization_id uuid,p_location_id uuid)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare r text := stabilis.labor_scope_role(p_organization_id,p_location_id);
begin
  return (select coalesce(jsonb_agg(to_jsonb(w) order by w.week_start desc),'[]'::jsonb)
    from stabilis.weekly_labor_reviews w
    where w.organization_id=p_organization_id and w.location_id=p_location_id
      and (w.status<>'draft' or r in ('STABILIS_ADMIN','STABILIS_ANALYST')));
end $$;

create function public.stabilis_save_labor_review(p_organization_id uuid,p_location_id uuid,p_review_id uuid,
  p_version integer,p_operation text,p_payload jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  role_name text := stabilis.labor_scope_role(p_organization_id,p_location_id);
  reviewer boolean := role_name in ('STABILIS_ADMIN','STABILIS_ANALYST');
  leader boolean := role_name in ('AREA_MANAGER','OWNER_EXECUTIVE');
  w stabilis.weekly_labor_reviews%rowtype;
  prior jsonb; entry jsonb; gm boolean;
  assignee uuid; member_name text; observed numeric; amount numeric; normalized jsonb; m jsonb;
  note text; period_start date; due date; next_review date;
begin
  if jsonb_typeof(p_payload) is distinct from 'object' or octet_length(p_payload::text)>26000 then
    raise exception 'Supply a valid review request';
  end if;
  if p_operation='create' then
    if not reviewer then raise exception 'Analyst access required' using errcode='42501'; end if;
    if p_review_id is not null or p_version is distinct from 0 then raise exception 'Invalid initial review version'; end if;
    period_start := stabilis.labor_closed_week(p_payload,p_location_id);
    normalized := jsonb_strip_nulls(p_payload->'inputs');
    m := stabilis.labor_metrics(normalized);
    note := stabilis.labor_required_text(p_payload,'source');
    insert into stabilis.weekly_labor_reviews(organization_id,location_id,week_start,inputs,metrics,source)
    values(p_organization_id,p_location_id,period_start,normalized,m,note)
    on conflict (organization_id,location_id,week_start) do nothing returning * into w;
    if not found then
      select * into strict w from stabilis.weekly_labor_reviews where organization_id=p_organization_id
        and location_id=p_location_id and week_start=period_start for update;
      if w.inputs=normalized and w.source=note then return to_jsonb(w); end if;
      raise exception 'A review exists for this location and week. Open it to correct the inputs.' using errcode='23505';
    end if;
    note := null;
  else
    select * into w from stabilis.weekly_labor_reviews where id=p_review_id and organization_id=p_organization_id and location_id=p_location_id for update;
    if not found or (w.status='draft' and not reviewer) then raise exception 'Review unavailable' using errcode='42501'; end if;
    if w.version is distinct from p_version then
      -- A browser retry after a lost response may return its own last completed mutation.
      if w.version=p_version+1 and exists(select 1 from stabilis.weekly_labor_audit a
        where a.review_id=w.id and a.version=w.version and a.actor_id=auth.uid() and a.operation=p_operation and a.payload=p_payload)
        then return to_jsonb(w); end if;
      raise exception 'Review changed. Refresh before trying again.' using errcode='40001';
    end if;
    prior := to_jsonb(w)-'history';
    gm := role_name='GENERAL_MANAGER' and auth.uid()::text=w.action->>'assignee_id';
    case p_operation
    when 'revise' then
      if not reviewer or w.status<>'draft' then raise exception 'Revisions require an analyst-owned draft'; end if;
      w.inputs := jsonb_strip_nulls(p_payload->'inputs');
      w.metrics := stabilis.labor_metrics(w.inputs);
      w.source := stabilis.labor_required_text(p_payload,'source');
    when 'release' then
      if not reviewer or w.status<>'draft' then raise exception 'A draft and analyst approval are required'; end if;
      note := stabilis.labor_required_text(p_payload,'note');
      w.status := 'released';
    when 'assign' then
      if not leader or w.status not in ('released','assigned','change_requested') then raise exception 'Leader approval of a released review required'; end if;
      assignee := stabilis.labor_required_text(p_payload,'assignee_id')::uuid;
      select a.display_name into member_name from stabilis.labor_review_assignees a join stabilis.memberships mm
        on mm.organization_id=a.organization_id and mm.profile_id=a.profile_id and mm.status='ACTIVE' and mm.role::text='GENERAL_MANAGER'
        join stabilis.membership_locations g on g.membership_id=mm.id and g.location_id=a.location_id
        where a.organization_id=w.organization_id and a.location_id=w.location_id and a.profile_id=assignee;
      if not found then raise exception 'Choose an enrolled location GM'; end if;
      due := stabilis.labor_date(p_payload,'due_date');
      next_review := stabilis.labor_date(p_payload,'next_review');
      if due < w.week_start or next_review < due then raise exception 'Check the due and next-review dates'; end if;
      w.action := jsonb_build_object('title',stabilis.labor_required_text(p_payload,'title'),'assignee_id',assignee,
        'assignee_name',member_name,'due_date',due,'next_review',next_review,'approved_by',auth.uid());
      w.status := 'assigned';
    when 'accept' then
      if gm is not true or w.status<>'assigned' then raise exception 'Assigned GM and outstanding assignment required'; end if;
      w.action := w.action || jsonb_build_object('accepted_at',now());
      w.status := 'accepted';
    when 'request_change' then
      if gm is not true or w.status<>'assigned' then raise exception 'Assigned GM and outstanding assignment required'; end if;
      note := stabilis.labor_required_text(p_payload,'note');
      w.action := w.action || jsonb_build_object('change_note',note);
      w.status := 'change_requested';
    when 'submit_evidence' then
      if gm is not true or w.status<>'accepted' then raise exception 'Assigned GM and accepted action required'; end if;
      note := stabilis.labor_required_text(p_payload,'note');
      w.action := w.action || jsonb_build_object('evidence',note,'evidence_at',now(),'evidence_by',auth.uid());
      w.status := 'evidence_submitted';
    when 'compare' then
      if not (reviewer or leader) or w.status not in ('evidence_submitted','compared') then raise exception 'Evidence and reviewer or leader access required'; end if;
      period_start := stabilis.labor_closed_week(p_payload,p_location_id);
      if period_start<w.week_start+7 or (period_start-w.week_start)%7<>0 then raise exception 'Select a later aligned fiscal week'; end if;
      if jsonb_typeof(p_payload->'comparable') is distinct from 'boolean' then raise exception 'Confirm whether the weeks are comparable'; end if;
      normalized := jsonb_strip_nulls(p_payload->'inputs');
      m := stabilis.labor_metrics(normalized);
      note := stabilis.labor_required_text(p_payload,'note');
      if (p_payload->>'comparable')::boolean then
        observed := (w.metrics->>'total_over')::numeric-(m->>'total_over')::numeric;
      end if;
      w.followup := jsonb_build_object('week_start',period_start,'inputs',normalized,'metrics',m,'source',stabilis.labor_required_text(p_payload,'source'),
        'comparable',p_payload->'comparable','note',note,'observed_change',observed,'reviewed_by',auth.uid());
      w.status := 'compared';
    when 'reopen' then
      if not (reviewer or leader) or w.status not in ('evidence_submitted','compared','verified') then raise exception 'Submitted evidence and reviewer or leader access required'; end if;
      note := stabilis.labor_required_text(p_payload,'note');
      w.followup := null; w.verification := null;
      w.action := w.action-'evidence'-'evidence_at'-'evidence_by';
      w.status := 'accepted';
    when 'verify' then
      if role_name<>'OWNER_EXECUTIVE' or w.status<>'compared' then raise exception 'Client owner must record finance validation after comparison'; end if;
      observed := (w.followup->>'observed_change')::numeric;
      if jsonb_typeof(p_payload->'amount') is distinct from 'number' then raise exception 'Supply a numeric validated amount'; end if;
      amount := (p_payload->>'amount')::numeric;
      if observed is null or observed<=0 or amount<=0 or amount>observed or amount<>round(amount,2) then
        raise exception 'Verified dollars require positive comparable change and cannot exceed observed change';
      end if;
      w.verification := jsonb_build_object('amount',amount,'finance_reference',stabilis.labor_required_text(p_payload,'finance_reference'),
        'attribution',stabilis.labor_required_text(p_payload,'attribution'),'overlap_check',stabilis.labor_required_text(p_payload,'overlap_check'),
        'recorded_by',auth.uid(),'recorded_at',now());
      w.status := 'verified';
    else raise exception 'Unknown review operation';
    end case;
    w.version := w.version+1;
  end if;
  entry := jsonb_strip_nulls(jsonb_build_object('at',now(),'operation',p_operation,'role',role_name,'note',note,'version',w.version));
  w.history := w.history || jsonb_build_array(entry);
  update stabilis.weekly_labor_reviews set version=w.version,status=w.status,source=w.source,inputs=w.inputs,metrics=w.metrics,
    action=w.action,followup=w.followup,verification=w.verification,history=w.history,updated_at=now()
    where id=w.id returning * into w;
  insert into stabilis.weekly_labor_audit(review_id,version,actor_id,operation,payload,previous_state)
    values(w.id,w.version,auth.uid(),p_operation,p_payload,prior);
  return to_jsonb(w);
end $$;

revoke all on function stabilis.labor_metrics(jsonb),stabilis.labor_required_text(jsonb,text),stabilis.labor_date(jsonb,text),
  stabilis.labor_scope_role(uuid,uuid),stabilis.labor_closed_week(jsonb,uuid) from public,anon,authenticated;
revoke all on function public.stabilis_labor_assignees(uuid,uuid),
  public.stabilis_enroll_labor_assignee(uuid,uuid,text),public.stabilis_labor_reviews(uuid,uuid),
  public.stabilis_save_labor_review(uuid,uuid,uuid,integer,text,jsonb) from public,anon;
grant execute on function public.stabilis_labor_assignees(uuid,uuid),
  public.stabilis_enroll_labor_assignee(uuid,uuid,text),public.stabilis_labor_reviews(uuid,uuid),
  public.stabilis_save_labor_review(uuid,uuid,uuid,integer,text,jsonb) to authenticated;
commit;
