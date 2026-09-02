-- Secure controlled-pilot CSV/XLSX intake registration and state finalization.

create or replace function public.stabilis_register_raw_upload(
  p_organization_id uuid,
  p_original_filename text,
  p_content_type text,
  p_size_bytes bigint,
  p_sha256 text,
  p_storage_path text,
  p_source_system text default null,
  p_reporting_period text default null
) returns jsonb
language plpgsql
set search_path=public,stabilis,pg_temp
as $$
declare v_existing uuid; v_file uuid; v_job uuid;
begin
  if auth.uid() is null or not stabilis.can_write_org(p_organization_id) then raise exception 'not authorized' using errcode='42501'; end if;
  if p_storage_path is null or split_part(p_storage_path,'/',1) <> p_organization_id::text then raise exception 'invalid tenant storage path' using errcode='42501'; end if;
  if p_size_bytes <= 0 or p_size_bytes > 52428800 then raise exception 'file size not permitted'; end if;
  if p_sha256 !~ '^[0-9a-f]{64}$' then raise exception 'invalid sha256'; end if;
  if lower(coalesce(p_original_filename,'')) !~ '\.(csv|xlsx)$' then raise exception 'only CSV or XLSX pilot files are permitted'; end if;
  select id into v_existing from stabilis.raw_files where organization_id=p_organization_id and sha256=p_sha256 order by uploaded_at desc limit 1;
  if v_existing is not null then return jsonb_build_object('duplicate',true,'raw_file_id',v_existing,'ingestion_job_id',null); end if;
  insert into stabilis.raw_files(organization_id,uploaded_by,filename,original_filename,content_type,size_bytes,sha256,storage_bucket,storage_path,source_system,reporting_period,processing_status,schema_version,version_number,duplicate_decision)
  values(p_organization_id,auth.uid(),regexp_replace(p_original_filename,'[^A-Za-z0-9._-]','_','g'),p_original_filename,left(p_content_type,120),p_size_bytes,p_sha256,'stabilis-raw',p_storage_path,left(p_source_system,120),left(p_reporting_period,120),'PENDING_UPLOAD','RAW-v1',1,'NEW') returning id into v_file;
  insert into stabilis.ingestion_jobs(organization_id,raw_file_id,state,code_version,schema_version,errors,warnings,record_count,idempotency_key)
  values(p_organization_id,v_file,'PENDING_UPLOAD','stabilis-pilot-v1','RAW-v1','[]'::jsonb,'[]'::jsonb,0,p_organization_id::text||':'||p_sha256) returning id into v_job;
  insert into stabilis.audit_events(organization_id,actor_id,action,entity_type,entity_id,new_state)
  values(p_organization_id,auth.uid(),'RAW_UPLOAD_PREPARED','raw_file',v_file,jsonb_build_object('storage_path',p_storage_path,'sha256',p_sha256,'ingestion_job_id',v_job));
  return jsonb_build_object('duplicate',false,'raw_file_id',v_file,'ingestion_job_id',v_job);
end $$;
revoke all on function public.stabilis_register_raw_upload(uuid,text,text,bigint,text,text,text,text) from public,anon;
grant execute on function public.stabilis_register_raw_upload(uuid,text,text,bigint,text,text,text,text) to authenticated;

create or replace function public.stabilis_set_raw_upload_state(
  p_organization_id uuid,p_raw_file_id uuid,p_state text,p_error text default null
) returns void
language plpgsql
set search_path=public,stabilis,pg_temp
as $$
declare v_state text:=upper(trim(p_state)); v_path text;
begin
  if auth.uid() is null or not stabilis.can_write_org(p_organization_id) then raise exception 'not authorized' using errcode='42501'; end if;
  if v_state not in ('UPLOADED','UPLOAD_FAILED') then raise exception 'invalid upload state'; end if;
  select storage_path into v_path from stabilis.raw_files where id=p_raw_file_id and organization_id=p_organization_id;
  if v_path is null then raise exception 'raw file unavailable' using errcode='42501'; end if;
  update stabilis.raw_files set processing_status=v_state where id=p_raw_file_id;
  update stabilis.ingestion_jobs
  set state=v_state,
      errors=case when v_state='UPLOAD_FAILED' then jsonb_build_array(jsonb_build_object('code','UPLOAD_FAILED','message',left(coalesce(p_error,'upload failed'),500))) else errors end,
      updated_at=now()
  where raw_file_id=p_raw_file_id and organization_id=p_organization_id;
  insert into stabilis.audit_events(organization_id,actor_id,action,entity_type,entity_id,new_state)
  values(p_organization_id,auth.uid(),'RAW_UPLOAD_STATE','raw_file',p_raw_file_id,jsonb_build_object('state',v_state,'storage_path',v_path));
end $$;
revoke all on function public.stabilis_set_raw_upload_state(uuid,uuid,text,text) from public,anon;
grant execute on function public.stabilis_set_raw_upload_state(uuid,uuid,text,text) to authenticated;
