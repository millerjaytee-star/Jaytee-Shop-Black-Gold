-- Ask Stabilis telemetry hardening.
-- Raw operator questions and prompt payloads are never stored. A database-internal
-- HMAC key fingerprints normalized questions for short-window duplicate protection.

alter table stabilis.intelligence_queries
  add column if not exists query_fingerprint text,
  add column if not exists dedupe_bucket bigint,
  add column if not exists question_chars integer,
  add column if not exists prompt_version text,
  add column if not exists context_builder_version text,
  add column if not exists output_schema_version text,
  add column if not exists evaluation_version text,
  add column if not exists input_tokens integer,
  add column if not exists cached_input_tokens integer,
  add column if not exists output_tokens integer,
  add column if not exists total_tokens integer,
  add column if not exists approximate_cost_usd numeric(14,8),
  add column if not exists estimated_netlify_credits numeric(14,6),
  add column if not exists currency text,
  add column if not exists pricing_version text,
  add column if not exists completed_at timestamptz;

alter table stabilis.intelligence_queries
  drop constraint if exists intelligence_queries_usage_nonnegative;
alter table stabilis.intelligence_queries
  add constraint intelligence_queries_usage_nonnegative check (
    coalesce(question_chars,0) >= 0
    and coalesce(input_tokens,0) >= 0
    and coalesce(cached_input_tokens,0) >= 0
    and coalesce(output_tokens,0) >= 0
    and coalesce(total_tokens,0) >= 0
    and coalesce(approximate_cost_usd,0) >= 0
    and coalesce(estimated_netlify_credits,0) >= 0
    and (input_tokens is null or cached_input_tokens is null or cached_input_tokens <= input_tokens)
  );

create unique index if not exists intelligence_queries_dedupe_uq
  on stabilis.intelligence_queries(organization_id, profile_id, query_fingerprint, dedupe_bucket)
  where query_fingerprint is not null and dedupe_bucket is not null;

create index if not exists intelligence_queries_model_created_idx
  on stabilis.intelligence_queries(organization_id, model_name, created_at desc);
create index if not exists intelligence_queries_category_created_idx
  on stabilis.intelligence_queries(organization_id, query_category, created_at desc);

-- Keep the fingerprint secret out of source control. Vault stores it encrypted on disk.
do $$
begin
  if not exists (select 1 from vault.secrets where name='stabilis_intelligence_fingerprint_key') then
    perform vault.create_secret(
      encode(gen_random_bytes(32),'hex'),
      'stabilis_intelligence_fingerprint_key',
      'Internal HMAC key for privacy-preserving Ask Stabilis duplicate detection'
    );
  end if;
end $$;

-- Provider/cost telemetry is internal operational data. Ordinary customer users
-- do not receive table-level visibility even for their own request rows.
drop policy if exists intelligence_queries_read on stabilis.intelligence_queries;
create policy intelligence_queries_internal_read on stabilis.intelligence_queries
for select to authenticated
using (stabilis.is_internal_reviewer(organization_id));

create or replace function public.stabilis_begin_intelligence_query(
  p_organization_id uuid,
  p_location_scope jsonb,
  p_query_category text,
  p_model_provider text,
  p_model_name text,
  p_question text,
  p_prompt_version text,
  p_context_builder_version text,
  p_output_schema_version text,
  p_evaluation_version text default null
) returns jsonb
language plpgsql
security definer
set search_path=public,stabilis,vault,extensions,pg_temp
as $$
declare
  v_profile uuid := auth.uid();
  v_normalized text;
  v_secret text;
  v_fingerprint text;
  v_bucket bigint;
  v_id uuid;
  v_location text;
begin
  if v_profile is null or not stabilis.is_member(p_organization_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  if p_location_scope is not null and jsonb_typeof(p_location_scope) <> 'array' then
    raise exception 'location scope must be an array' using errcode='22023';
  end if;
  for v_location in select jsonb_array_elements_text(coalesce(p_location_scope,'[]'::jsonb)) loop
    if not stabilis.can_access_location(p_organization_id,v_location::uuid) then
      raise exception 'location not authorized' using errcode='42501';
    end if;
  end loop;
  if length(coalesce(p_question,'')) < 2 or length(p_question) > 1400 then
    raise exception 'question length invalid' using errcode='22023';
  end if;

  select decrypted_secret into v_secret
  from vault.decrypted_secrets
  where name='stabilis_intelligence_fingerprint_key'
  limit 1;
  if v_secret is null then
    raise exception 'telemetry fingerprint key unavailable' using errcode='55000';
  end if;

  v_normalized := lower(regexp_replace(trim(p_question),'\s+',' ','g'));
  v_fingerprint := encode(hmac(convert_to(v_normalized,'UTF8'),convert_to(v_secret,'UTF8'),'sha256'),'hex');
  v_bucket := floor(extract(epoch from clock_timestamp()) / 10)::bigint;

  insert into stabilis.intelligence_queries(
    organization_id,profile_id,location_scope,query_category,model_provider,model_name,
    model_version,response_status,evidence_refs,query_fingerprint,dedupe_bucket,
    question_chars,prompt_version,context_builder_version,output_schema_version,evaluation_version
  ) values (
    p_organization_id,v_profile,coalesce(p_location_scope,'[]'::jsonb),
    left(coalesce(p_query_category,'other'),80),left(coalesce(p_model_provider,'unknown'),80),
    left(coalesce(p_model_name,'unknown'),120),null,'started','[]'::jsonb,v_fingerprint,v_bucket,
    length(p_question),left(p_prompt_version,120),left(p_context_builder_version,120),
    left(p_output_schema_version,120),left(p_evaluation_version,120)
  )
  on conflict (organization_id,profile_id,query_fingerprint,dedupe_bucket)
    where query_fingerprint is not null and dedupe_bucket is not null
  do nothing
  returning id into v_id;

  if v_id is null then
    select id into v_id
    from stabilis.intelligence_queries
    where organization_id=p_organization_id
      and profile_id=v_profile
      and query_fingerprint=v_fingerprint
      and dedupe_bucket=v_bucket
    order by created_at desc
    limit 1;
    return jsonb_build_object('query_id',v_id,'duplicate',true);
  end if;

  return jsonb_build_object('query_id',v_id,'duplicate',false);
end $$;

revoke all on function public.stabilis_begin_intelligence_query(uuid,jsonb,text,text,text,text,text,text,text,text) from public,anon;
grant execute on function public.stabilis_begin_intelligence_query(uuid,jsonb,text,text,text,text,text,text,text,text) to authenticated;

create or replace function public.stabilis_finalize_intelligence_query(
  p_query_id uuid,
  p_organization_id uuid,
  p_response_status text,
  p_evidence_refs jsonb default '[]'::jsonb,
  p_latency_ms integer default null,
  p_error_code text default null,
  p_model_version text default null,
  p_input_tokens integer default null,
  p_cached_input_tokens integer default null,
  p_output_tokens integer default null,
  p_total_tokens integer default null,
  p_approximate_cost_usd numeric default null,
  p_estimated_netlify_credits numeric default null,
  p_currency text default null,
  p_pricing_version text default null
) returns boolean
language plpgsql
security definer
set search_path=public,stabilis,pg_temp
as $$
declare
  v_profile uuid := auth.uid();
  v_count integer;
begin
  if v_profile is null or not stabilis.is_member(p_organization_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  if coalesce(p_latency_ms,0) < 0
    or coalesce(p_input_tokens,0) < 0
    or coalesce(p_cached_input_tokens,0) < 0
    or coalesce(p_output_tokens,0) < 0
    or coalesce(p_total_tokens,0) < 0
    or coalesce(p_approximate_cost_usd,0) < 0
    or coalesce(p_estimated_netlify_credits,0) < 0
    or (p_input_tokens is not null and p_cached_input_tokens is not null and p_cached_input_tokens > p_input_tokens) then
    raise exception 'telemetry values invalid' using errcode='22023';
  end if;

  update stabilis.intelligence_queries
  set response_status=left(coalesce(p_response_status,'unknown'),40),
      evidence_refs=coalesce(p_evidence_refs,'[]'::jsonb),
      latency_ms=p_latency_ms,
      error_code=left(p_error_code,120),
      model_version=left(p_model_version,120),
      input_tokens=p_input_tokens,
      cached_input_tokens=p_cached_input_tokens,
      output_tokens=p_output_tokens,
      total_tokens=p_total_tokens,
      approximate_cost_usd=p_approximate_cost_usd,
      estimated_netlify_credits=p_estimated_netlify_credits,
      currency=left(p_currency,8),
      pricing_version=left(p_pricing_version,120),
      completed_at=now()
  where id=p_query_id
    and organization_id=p_organization_id
    and profile_id=v_profile;
  get diagnostics v_count = row_count;
  if v_count <> 1 then
    raise exception 'query not authorized' using errcode='42501';
  end if;
  return true;
end $$;

revoke all on function public.stabilis_finalize_intelligence_query(uuid,uuid,text,jsonb,integer,text,text,integer,integer,integer,integer,numeric,numeric,text,text) from public,anon;
grant execute on function public.stabilis_finalize_intelligence_query(uuid,uuid,text,jsonb,integer,text,text,integer,integer,integer,integer,numeric,numeric,text,text) to authenticated;

-- Repair feedback persistence: the prior invoker function could not insert because
-- authenticated users only had SELECT on the underlying table.
create or replace function public.stabilis_submit_intelligence_feedback(
  p_organization_id uuid,p_query_id uuid,p_rating text,p_reason text default null,p_comment text default null
) returns uuid
language plpgsql
security definer
set search_path=public,stabilis,pg_temp
as $$
declare v_id uuid;
begin
  if auth.uid() is null or not stabilis.is_member(p_organization_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  if not exists(
    select 1 from stabilis.intelligence_queries q
    where q.id=p_query_id and q.organization_id=p_organization_id and q.profile_id=auth.uid()
  ) then
    raise exception 'query not authorized' using errcode='42501';
  end if;
  if upper(coalesce(p_rating,'')) not in ('HELPFUL','NOT_HELPFUL') then
    raise exception 'invalid rating' using errcode='22023';
  end if;
  insert into stabilis.intelligence_query_feedback(organization_id,query_id,profile_id,rating,reason,comment)
  values(
    p_organization_id,p_query_id,auth.uid(),upper(p_rating),
    nullif(upper(coalesce(p_reason,'')),''),left(p_comment,2000)
  )
  on conflict(query_id,profile_id) do update
    set rating=excluded.rating,reason=excluded.reason,comment=excluded.comment,created_at=now()
  returning id into v_id;
  return v_id;
end $$;

revoke all on function public.stabilis_submit_intelligence_feedback(uuid,uuid,text,text,text) from public,anon;
grant execute on function public.stabilis_submit_intelligence_feedback(uuid,uuid,text,text,text) to authenticated;

create or replace function public.stabilis_intelligence_usage_summary(
  p_organization_id uuid,
  p_since timestamptz default (now() - interval '7 days')
) returns jsonb
language plpgsql
stable
security definer
set search_path=public,stabilis,pg_temp
as $$
declare v_result jsonb;
begin
  if auth.uid() is null or not stabilis.is_internal_reviewer(p_organization_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  select jsonb_build_object(
    'since',p_since,
    'requests',count(*),
    'input_tokens',coalesce(sum(input_tokens),0),
    'cached_input_tokens',coalesce(sum(cached_input_tokens),0),
    'output_tokens',coalesce(sum(output_tokens),0),
    'total_tokens',coalesce(sum(total_tokens),0),
    'approximate_cost_usd',coalesce(sum(approximate_cost_usd),0),
    'estimated_netlify_credits',coalesce(sum(estimated_netlify_credits),0),
    'average_latency_ms',round(avg(latency_ms)::numeric,2),
    'errors',count(*) filter (where response_status in ('provider_error','malformed_output','provider_unavailable')),
    'by_model',coalesce((
      select jsonb_agg(to_jsonb(x) order by x.requests desc)
      from (
        select model_name,model_version,count(*) requests,
          coalesce(sum(total_tokens),0) total_tokens,
          coalesce(sum(approximate_cost_usd),0) approximate_cost_usd
        from stabilis.intelligence_queries
        where organization_id=p_organization_id and created_at>=p_since
        group by model_name,model_version
      ) x
    ),'[]'::jsonb),
    'by_query_category',coalesce((
      select jsonb_agg(to_jsonb(x) order by x.requests desc)
      from (
        select query_category,count(*) requests,
          coalesce(sum(total_tokens),0) total_tokens,
          coalesce(sum(approximate_cost_usd),0) approximate_cost_usd
        from stabilis.intelligence_queries
        where organization_id=p_organization_id and created_at>=p_since
        group by query_category
      ) x
    ),'[]'::jsonb)
  ) into v_result
  from stabilis.intelligence_queries
  where organization_id=p_organization_id and created_at>=p_since;
  return v_result;
end $$;

revoke all on function public.stabilis_intelligence_usage_summary(uuid,timestamptz) from public,anon;
grant execute on function public.stabilis_intelligence_usage_summary(uuid,timestamptz) to authenticated;

comment on table stabilis.intelligence_queries is
'Internal Ask Stabilis request telemetry. No raw question or prompt payload is stored. Retain operational telemetry for 90 days unless a shorter customer contract or legal requirement applies.';
comment on function public.stabilis_begin_intelligence_query(uuid,jsonb,text,text,text,text,text,text,text,text) is
'Creates an authorized Ask Stabilis telemetry row and returns duplicate=true for repeated normalized questions inside a 10-second bucket. Raw question text is HMACed in-database and not stored.';
comment on function public.stabilis_intelligence_usage_summary(uuid,timestamptz) is
'Internal-reviewer-only usage summary. AI provider costs are operational telemetry and never customer financial opportunity or Verified Financial Impact.';
