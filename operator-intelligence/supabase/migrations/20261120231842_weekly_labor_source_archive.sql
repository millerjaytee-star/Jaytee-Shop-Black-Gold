-- Private weekly labor source references and version history.
-- The existing tenant-wide intake remains available outside the reserved weekly folder.
begin;

do $$
begin
  if not exists (select 1 from storage.buckets where id='stabilis-raw' and not public)
     or not exists (select 1 from pg_class where oid='storage.objects'::regclass and relrowsecurity)
     or to_regprocedure('storage.allow_any_operation(text[])') is null then
    raise exception 'Weekly archives require the private stabilis-raw bucket, Storage RLS and operation-aware policies';
  end if;
end $$;

create table stabilis.weekly_labor_source_files (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references stabilis.organizations(id),
  location_id uuid not null references stabilis.locations(id),
  week_start date not null,
  filename text not null,
  sha256 text not null,
  size_bytes bigint not null,
  object_path text not null unique,
  retain_through date not null,
  prepared_by uuid not null,
  prepared_at timestamptz not null default now(),
  archived_at timestamptz,
  unique (organization_id,location_id,week_start,sha256)
);
alter table stabilis.weekly_labor_source_files enable row level security;
revoke all on stabilis.weekly_labor_source_files from public, anon, authenticated;

create function stabilis.can_archive_weekly_labor(p_org uuid,p_location uuid) returns boolean
language sql stable set search_path = '' as $$
  select coalesce(auth.uid() is not null
    and stabilis.role_in_org(p_org)::text in ('STABILIS_ADMIN','STABILIS_ANALYST')
    and stabilis.can_access_location(p_org,p_location)
    and exists (select 1 from stabilis.locations where id=p_location and organization_id=p_org),false)
$$;
revoke all on function stabilis.can_archive_weekly_labor(uuid,uuid) from public, anon, authenticated;

-- Storage policies use a boolean access predicate. The archive registry itself remains private.
create function public.stabilis_weekly_source_object_access(p_path text,p_writing boolean) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from stabilis.weekly_labor_source_files f
    where f.object_path=p_path
      and (case when p_writing then f.archived_at is null else f.archived_at is not null end)
      and f.retain_through>=current_date
      and stabilis.can_archive_weekly_labor(f.organization_id,f.location_id)
  )
$$;
revoke all on function public.stabilis_weekly_source_object_access(text,boolean) from public;
grant execute on function public.stabilis_weekly_source_object_access(text,boolean) to anon, authenticated;

-- Restrictive policies guard the reserved folder even when a broader legacy tenant policy applies.
create policy weekly_labor_source_read_limit on storage.objects as restrictive for select
using (case when bucket_id='stabilis-raw' and split_part(name,'/',2)='weekly-labor'
  then storage.allow_any_operation(array['storage.object.get_authenticated','object.get_authenticated_info'])
    and public.stabilis_weekly_source_object_access(name,false) else true end);
create policy weekly_labor_source_write_limit on storage.objects as restrictive for insert
with check (case when bucket_id='stabilis-raw' and split_part(name,'/',2)='weekly-labor'
  then storage.allow_any_operation(array['storage.object.upload'])
    and public.stabilis_weekly_source_object_access(name,true) else true end);
create policy weekly_labor_source_no_replace on storage.objects as restrictive for update
using (bucket_id<>'stabilis-raw' or split_part(name,'/',2)<>'weekly-labor')
with check (bucket_id<>'stabilis-raw' or split_part(name,'/',2)<>'weekly-labor');
create policy weekly_labor_source_no_client_delete on storage.objects as restrictive for delete
using (bucket_id<>'stabilis-raw' or split_part(name,'/',2)<>'weekly-labor');

create policy weekly_labor_source_read on storage.objects for select to authenticated
using (bucket_id='stabilis-raw' and split_part(name,'/',2)='weekly-labor'
  and public.stabilis_weekly_source_object_access(name,false));
create policy weekly_labor_source_write on storage.objects for insert to authenticated
with check (bucket_id='stabilis-raw' and split_part(name,'/',2)='weekly-labor'
  and public.stabilis_weekly_source_object_access(name,true));

create function public.stabilis_prepare_weekly_source(
  p_organization_id uuid,p_location_id uuid,p_week_start date,p_filename text,
  p_sha256 text,p_size_bytes bigint,p_retain_through date
) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
  source stabilis.weekly_labor_source_files%rowtype;
  target_id uuid := gen_random_uuid();
  extension text := lower(substring(p_filename from '\.([a-zA-Z]+)$'));
begin
  if not stabilis.can_archive_weekly_labor(p_organization_id,p_location_id) then
    raise exception 'Authorized analyst access required' using errcode='42501';
  end if;
  perform stabilis.labor_closed_week(jsonb_build_object('week_start',p_week_start),p_location_id);
  if extension is null or extension not in ('csv','tsv','xlsx') or length(p_filename)>180
     or p_sha256 is null or p_sha256 !~ '^[0-9a-f]{64}$' or p_size_bytes is null
     or p_size_bytes not between 1 and 5242880
     or p_retain_through is null or p_retain_through<current_date or not isfinite(p_retain_through) then
    raise exception 'Supply a valid file, checksum and signed retention date';
  end if;
  insert into stabilis.weekly_labor_source_files(id,organization_id,location_id,week_start,filename,
    sha256,size_bytes,object_path,retain_through,prepared_by)
  values(target_id,p_organization_id,p_location_id,p_week_start,p_filename,p_sha256,p_size_bytes,
    p_organization_id::text||'/weekly-labor/'||p_location_id::text||'/'||target_id::text||'.'||extension,
    p_retain_through,auth.uid())
  on conflict (organization_id,location_id,week_start,sha256) do nothing returning * into source;
  if not found then
    select * into strict source from stabilis.weekly_labor_source_files
    where organization_id=p_organization_id and location_id=p_location_id
      and week_start=p_week_start and sha256=p_sha256;
    if source.retain_through<>p_retain_through or source.size_bytes<>p_size_bytes then
      raise exception 'This source already has a different signed retention date or file size. Ask the pilot administrator before reusing it.';
    end if;
  end if;
  return jsonb_build_object('id',source.id,'path',source.object_path,'archived',source.archived_at is not null);
end $$;

create function public.stabilis_finish_weekly_source(p_organization_id uuid,p_location_id uuid,p_source_id uuid)
returns void language plpgsql security definer set search_path = '' as $$
declare source stabilis.weekly_labor_source_files%rowtype;
begin
  if not stabilis.can_archive_weekly_labor(p_organization_id,p_location_id) then
    raise exception 'Authorized analyst access required' using errcode='42501';
  end if;
  select * into source from stabilis.weekly_labor_source_files
    where id=p_source_id and organization_id=p_organization_id and location_id=p_location_id
      and retain_through>=current_date for update;
  if not found then
    raise exception 'Archive unavailable' using errcode='42501';
  end if;
  if not exists (select 1 from storage.objects o
    where o.bucket_id='stabilis-raw' and o.name=source.object_path and o.metadata->>'size'=source.size_bytes::text)
  then raise exception 'Uploaded source could not be confirmed. Retry or save the mapped figures without archiving.'; end if;
  update stabilis.weekly_labor_source_files set archived_at=coalesce(archived_at,now()) where id=source.id;
end $$;

create function stabilis.validate_weekly_source_history() returns trigger
language plpgsql set search_path = '' as $$
declare
  imports jsonb := new.payload->'imports';
  source_week date;
  review stabilis.weekly_labor_reviews%rowtype;
  report jsonb;
  group_record jsonb;
  allowed_fields text[];
  kind text;
  key text;
  value jsonb;
begin
  if imports is null then return new; end if;
  if new.operation not in ('create','revise','correct','compare') or jsonb_typeof(imports) is distinct from 'array' then
    raise exception 'Weekly mapping metadata must accompany period figures';
  end if;
  if jsonb_array_length(imports)>3 then raise exception 'Supply one source mapping per report type'; end if;
  select * into strict review from stabilis.weekly_labor_reviews where id=new.review_id;
  source_week := case when new.operation='compare' then (review.followup->>'week_start')::date else review.week_start end;
  if new.payload ? 'week_start' and (new.payload->>'week_start')::date is distinct from source_week then
    raise exception 'Mapped sources must match this fiscal week';
  end if;
  if jsonb_array_length(imports)<>(select count(distinct v->>'type') from jsonb_array_elements(imports) as a(v)) then
    raise exception 'Supply one source mapping per report type';
  end if;
  for report in select v from jsonb_array_elements(imports) as a(v) loop
    kind := report->>'type';
    allowed_fields := case kind when 'sales' then array['actual_sales','forecast_sales']
      when 'schedule' then array['scheduled_hours','scheduled_cost'] when 'payroll' then array['actual_hours','actual_cost'] end;
    if allowed_fields is null or jsonb_typeof(report->'mapping') is distinct from 'object'
       or jsonb_typeof(report->'totals') is distinct from 'object'
       or jsonb_typeof(report->'groups') is distinct from 'array'
       or jsonb_typeof(report->'gaps') is distinct from 'array'
       or coalesce(report->>'header_row','') !~ '^([1-9]|1[0-9]|2[0-5])$'
       or coalesce(report->>'coverage','') !~ '^[0-7]$'
       or coalesce(report->>'row_count','') !~ '^[1-9][0-9]{0,4}$'
       or length(coalesce(report->>'filename','')) not between 1 and 180
       or length(coalesce(report->>'sheet','')) not between 1 and 100
       or length(coalesce(report->>'source_location','')) not between 1 and 100
       or (report->>'sha256' is not null and report->>'sha256' !~ '^[0-9a-f]{64}$') then
      raise exception 'Invalid weekly source mapping';
    end if;
    if jsonb_array_length(report->'groups')>24 or jsonb_array_length(report->'gaps')>8
       or (kind='sales' and jsonb_array_length(report->'groups')>0)
       or exists (select 1 from jsonb_each(report->'mapping') e(k,v)
         where not (k=any(allowed_fields||array['date','location','role','daypart']))
           or jsonb_typeof(v)<>'string' or length(v#>>'{}') not between 1 and 120)
       or exists (select 1 from jsonb_array_elements(report->'gaps') e(v)
         where jsonb_typeof(v)<>'string' or length(v#>>'{}') not between 1 and 140)
       or coalesce(report->'mapping'->>'date','')='' then
      raise exception 'Invalid weekly source column definitions';
    end if;
    foreach key in array allowed_fields loop
      value := report->'totals'->key;
      if value is null or coalesce(new.payload->'inputs'->key,'null'::jsonb)<>value then
        raise exception 'Mapped % does not match the saved weekly input',key;
      end if;
      if value<>'null'::jsonb and (jsonb_typeof(value)<>'number' or report->>'coverage'<>'7') then
        raise exception 'Measured weekly inputs require seven days of source coverage';
      end if;
    end loop;
    for group_record in select v from jsonb_array_elements(report->'groups') as a(v) loop
      if jsonb_typeof(group_record)<>'object' or not (group_record ?| array['role','daypart']) then
        raise exception 'Include a role or daypart label in each source group';
      end if;
      for key,value in select * from jsonb_each(group_record) loop
        if key in ('role','daypart') then
          if not (report->'mapping' ? key) or jsonb_typeof(value)<>'string' or length(value#>>'{}') not between 1 and 100 then
            raise exception 'Invalid weekly source group label';
          end if;
        elsif not (key=any(allowed_fields)) or not (report->'mapping' ? key)
           or report->>'coverage'<>'7' or jsonb_typeof(value)<>'number'
           or (value#>>'{}')::numeric<0 or (value#>>'{}')::numeric>1000000000000 then
          raise exception 'Invalid weekly source group measure';
        end if;
      end loop;
    end loop;
    if report->>'archive_id' is not null and not exists (
      select 1 from stabilis.weekly_labor_source_files f
      where f.id=(report->>'archive_id')::uuid and f.organization_id=review.organization_id
        and f.location_id=review.location_id and f.week_start=source_week
        and f.sha256=report->>'sha256' and f.archived_at is not null and f.retain_through>=current_date
        and stabilis.can_archive_weekly_labor(f.organization_id,f.location_id)
    ) then raise exception 'Source archive does not belong to this authorized location and week' using errcode='42501'; end if;
  end loop;
  return new;
end $$;
revoke all on function stabilis.validate_weekly_source_history() from public, anon, authenticated;
create trigger validate_weekly_source_history before insert on stabilis.weekly_labor_audit
for each row execute function stabilis.validate_weekly_source_history();

create function public.stabilis_weekly_source_history(p_organization_id uuid,p_location_id uuid,p_review_id uuid)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
begin
  if not stabilis.can_archive_weekly_labor(p_organization_id,p_location_id) or not exists (
    select 1 from stabilis.weekly_labor_reviews w
    where w.id=p_review_id and w.organization_id=p_organization_id and w.location_id=p_location_id
  ) then raise exception 'Source history unavailable' using errcode='42501'; end if;
  return (
    select coalesce(jsonb_agg(jsonb_build_object(
      'version',a.version,'operation',a.operation,'recorded_at',a.created_at,
      'week_start',a.payload->'week_start','source',a.payload->'source',
      'reports',(select coalesce(jsonb_agg((report-'archive_id')||jsonb_build_object('archive',
        case when f.id is not null then jsonb_build_object('id',f.id,'retain_through',f.retain_through,
          'path',case when f.retain_through>=current_date and exists (
            select 1 from storage.objects o where o.bucket_id='stabilis-raw' and o.name=f.object_path
          ) then f.object_path end) end)), '[]'::jsonb)
        from jsonb_array_elements(coalesce(a.payload->'imports','[]')) as j(report)
        left join stabilis.weekly_labor_source_files f on f.id=(report->>'archive_id')::uuid)
    ) order by a.version desc), '[]'::jsonb)
    from stabilis.weekly_labor_audit a
    where a.review_id=p_review_id and a.operation in ('create','revise','correct','compare')
  );
end $$;

revoke all on function public.stabilis_prepare_weekly_source(uuid,uuid,date,text,text,bigint,date),
  public.stabilis_finish_weekly_source(uuid,uuid,uuid),public.stabilis_weekly_source_history(uuid,uuid,uuid) from public,anon;
grant execute on function public.stabilis_prepare_weekly_source(uuid,uuid,date,text,text,bigint,date),
  public.stabilis_finish_weekly_source(uuid,uuid,uuid),public.stabilis_weekly_source_history(uuid,uuid,uuid) to authenticated;
commit;
