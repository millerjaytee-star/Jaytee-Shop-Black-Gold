-- Controlled-pilot action execution RPCs.
-- Actions may only originate from analyst-approved recommendations; VERIFIED remains reviewer-only.

create or replace function public.stabilis_create_action_from_opportunity(
  p_organization_id uuid,
  p_opportunity_id uuid,
  p_title text,
  p_start_date date,
  p_due_date date,
  p_notes text default null
) returns uuid
language plpgsql
set search_path=public,stabilis,pg_temp
as $$
declare
  v_opp stabilis.opportunities%rowtype;
  v_rec uuid;
  v_owner uuid := auth.uid();
  v_id uuid;
  v_baseline numeric;
  v_target numeric;
begin
  if auth.uid() is null or not stabilis.can_write_org(p_organization_id) then raise exception 'not authorized' using errcode='42501'; end if;
  select * into v_opp from stabilis.opportunities where id=p_opportunity_id and organization_id=p_organization_id;
  if not found then raise exception 'opportunity unavailable' using errcode='42501'; end if;
  if v_opp.location_id is not null and not stabilis.can_access_location(p_organization_id,v_opp.location_id) then raise exception 'location not authorized' using errcode='42501'; end if;
  select id into v_rec from stabilis.recommendations
  where opportunity_id=p_opportunity_id and organization_id=p_organization_id and review_status in ('ANALYST_APPROVED','ANALYST_EDITED')
  order by created_at desc limit 1;
  if v_rec is null then raise exception 'analyst-approved recommendation required before action creation'; end if;
  select current_value,benchmark_value into v_baseline,v_target from stabilis.findings where id=v_opp.finding_id;
  if p_due_date is not null and p_start_date is not null and p_due_date < p_start_date then raise exception 'due date cannot precede start date'; end if;
  insert into stabilis.actions(organization_id,recommendation_id,location_id,title,status,baseline,target,start_date,due_date,expected_financial_impact,owner_profile_id,notes)
  values(p_organization_id,v_rec,v_opp.location_id,left(p_title,240),'PLANNED',v_baseline,v_target,p_start_date,p_due_date,coalesce(v_opp.base_estimate,v_opp.annualized_value),v_owner,left(p_notes,4000))
  returning id into v_id;
  insert into stabilis.audit_events(organization_id,actor_id,action,entity_type,entity_id,new_state)
  values(p_organization_id,auth.uid(),'ACTION_CREATED','action',v_id,jsonb_build_object('opportunity_id',p_opportunity_id,'status','PLANNED'));
  return v_id;
end $$;
revoke all on function public.stabilis_create_action_from_opportunity(uuid,uuid,text,date,date,text) from public,anon;
grant execute on function public.stabilis_create_action_from_opportunity(uuid,uuid,text,date,date,text) to authenticated;

create or replace function public.stabilis_update_action_state(
  p_organization_id uuid,
  p_action_id uuid,
  p_status text,
  p_note text default null
) returns void
language plpgsql
set search_path=public,stabilis,pg_temp
as $$
declare
  v_action stabilis.actions%rowtype;
  v_status text := upper(replace(trim(p_status),' ','_'));
begin
  if auth.uid() is null or not stabilis.can_write_org(p_organization_id) then raise exception 'not authorized' using errcode='42501'; end if;
  select * into v_action from stabilis.actions where id=p_action_id and organization_id=p_organization_id;
  if not found then raise exception 'action unavailable' using errcode='42501'; end if;
  if v_action.location_id is not null and not stabilis.can_access_location(p_organization_id,v_action.location_id) then raise exception 'location not authorized' using errcode='42501'; end if;
  if v_status not in ('NEW','APPROVED','PLANNED','IN_PROGRESS','BLOCKED','COMPLETE','VERIFICATION_PENDING','VERIFIED','REJECTED') then raise exception 'invalid action status'; end if;
  if v_status='VERIFIED' and not stabilis.is_internal_reviewer(p_organization_id) then raise exception 'verification requires Stabilis reviewer' using errcode='42501'; end if;
  update stabilis.actions
  set status=v_status,
      notes=case when p_note is null then notes else concat_ws(E'\n',nullif(notes,''),left(p_note,2000)) end,
      updated_at=now()
  where id=p_action_id;
  insert into stabilis.action_updates(organization_id,action_id,status,note,changed_by)
  values(p_organization_id,p_action_id,v_status,left(p_note,2000),auth.uid());
  insert into stabilis.audit_events(organization_id,actor_id,action,entity_type,entity_id,previous_state,new_state)
  values(p_organization_id,auth.uid(),'ACTION_STATUS_UPDATED','action',p_action_id,jsonb_build_object('status',v_action.status),jsonb_build_object('status',v_status,'note',left(p_note,500)));
end $$;
revoke all on function public.stabilis_update_action_state(uuid,uuid,text,text) from public,anon;
grant execute on function public.stabilis_update_action_state(uuid,uuid,text,text) to authenticated;
