-- Keep customer insight feedback tenant-scoped and auditable.
create or replace function public.stabilis_submit_feedback(
  p_organization_id uuid,
  p_finding_id uuid default null,
  p_recommendation_id uuid default null,
  p_useful_rating text default null,
  p_disposition text default null,
  p_comment text default null
) returns uuid
language plpgsql
set search_path=public,stabilis,pg_temp
as $$
declare v_id uuid;
begin
  if auth.uid() is null or not stabilis.is_member(p_organization_id) then
    raise exception 'not authorized' using errcode='42501';
  end if;
  if p_finding_id is null and p_recommendation_id is null then
    raise exception 'finding or recommendation required';
  end if;
  if p_finding_id is not null and not exists(
    select 1 from stabilis.findings where id=p_finding_id and organization_id=p_organization_id
  ) then raise exception 'finding not authorized' using errcode='42501'; end if;
  if p_recommendation_id is not null and not exists(
    select 1 from stabilis.recommendations where id=p_recommendation_id and organization_id=p_organization_id
  ) then raise exception 'recommendation not authorized' using errcode='42501'; end if;
  insert into stabilis.insight_feedback(
    organization_id,finding_id,recommendation_id,profile_id,useful_rating,recommendation_disposition,comment
  ) values(
    p_organization_id,p_finding_id,p_recommendation_id,auth.uid(),p_useful_rating,p_disposition,left(p_comment,2000)
  ) returning id into v_id;
  insert into stabilis.audit_events(organization_id,actor_id,action,entity_type,entity_id,new_state)
  values(p_organization_id,auth.uid(),'FEEDBACK_SUBMITTED','insight_feedback',v_id,
    jsonb_build_object('useful_rating',p_useful_rating,'disposition',p_disposition));
  return v_id;
end $$;
revoke all on function public.stabilis_submit_feedback(uuid,uuid,uuid,text,text,text) from public,anon;
grant execute on function public.stabilis_submit_feedback(uuid,uuid,uuid,text,text,text) to authenticated;
