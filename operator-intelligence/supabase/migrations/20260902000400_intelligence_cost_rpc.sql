create or replace function public.stabilis_log_intelligence_query_v2(
  p_organization_id uuid,
  p_location_scope jsonb,
  p_query_category text,
  p_model_provider text,
  p_model_name text,
  p_model_version text,
  p_response_status text,
  p_evidence_refs jsonb default '[]'::jsonb,
  p_latency_ms integer default null,
  p_error_code text default null,
  p_query_fingerprint text default null,
  p_question_chars integer default null,
  p_prompt_version text default null,
  p_context_builder_version text default null,
  p_output_schema_version text default null,
  p_evaluation_version text default null,
  p_input_tokens integer default null,
  p_cached_input_tokens integer default null,
  p_output_tokens integer default null,
  p_estimated_cost_usd numeric default null,
  p_cost_basis text default null
) returns uuid
language plpgsql
security invoker
set search_path=public,stabilis,pg_temp
as $$
declare v_id uuid;
begin
  if auth.uid() is null or not stabilis.is_member(p_organization_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  if p_location_scope is not null and jsonb_typeof(p_location_scope) <> 'array' then
    raise exception 'location scope must be an array' using errcode='22023';
  end if;
  if coalesce(p_question_chars,0) < 0
    or coalesce(p_input_tokens,0) < 0
    or coalesce(p_cached_input_tokens,0) < 0
    or coalesce(p_output_tokens,0) < 0
    or coalesce(p_estimated_cost_usd,0) < 0 then
    raise exception 'usage values must be non-negative' using errcode='22023';
  end if;

  insert into stabilis.intelligence_queries(
    organization_id,profile_id,location_scope,query_category,model_provider,model_name,model_version,
    response_status,evidence_refs,latency_ms,error_code,query_fingerprint,question_chars,prompt_version,
    context_builder_version,output_schema_version,evaluation_version,input_tokens,cached_input_tokens,
    output_tokens,estimated_cost_usd,cost_basis
  ) values (
    p_organization_id,auth.uid(),coalesce(p_location_scope,'[]'::jsonb),left(coalesce(p_query_category,'other'),80),
    left(coalesce(p_model_provider,'unknown'),80),left(coalesce(p_model_name,'unknown'),120),left(p_model_version,120),
    left(coalesce(p_response_status,'unknown'),40),coalesce(p_evidence_refs,'[]'::jsonb),p_latency_ms,left(p_error_code,120),
    left(p_query_fingerprint,128),p_question_chars,left(p_prompt_version,120),left(p_context_builder_version,120),
    left(p_output_schema_version,120),left(p_evaluation_version,120),p_input_tokens,p_cached_input_tokens,p_output_tokens,
    p_estimated_cost_usd,left(p_cost_basis,160)
  ) returning id into v_id;
  return v_id;
end $$;

revoke all on function public.stabilis_log_intelligence_query_v2(uuid,jsonb,text,text,text,text,text,jsonb,integer,text,text,integer,text,text,text,text,integer,integer,integer,numeric,text) from public,anon;
grant execute on function public.stabilis_log_intelligence_query_v2(uuid,jsonb,text,text,text,text,text,jsonb,integer,text,text,integer,text,text,text,text,integer,integer,integer,numeric,text) to authenticated;
