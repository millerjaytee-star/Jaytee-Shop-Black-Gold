-- Read-only structural check for an approved staging or release database.
-- Run with psql -X -v ON_ERROR_STOP=1 -f; hosted behavior requires separate tests.
begin read only;

do $$
declare
  missing text;
begin
  select string_agg(required.table_name || '.' || required.column_name, ', ' order by required.table_name, required.column_name)
    into missing
  from (values
    ('organizations','id'), ('profiles','id'),
    ('locations','id'), ('locations','organization_id'), ('locations','timezone'),
    ('memberships','id'), ('memberships','organization_id'), ('memberships','profile_id'),
    ('memberships','role'), ('memberships','status'),
    ('membership_locations','membership_id'), ('membership_locations','location_id')
  ) as required(table_name,column_name)
  where not exists (
    select from information_schema.columns c
    where c.table_schema='stabilis' and c.table_name=required.table_name and c.column_name=required.column_name
  );

  if missing is not null then
    raise exception 'Weekly release foundation columns unavailable: %', missing;
  end if;
  if to_regprocedure('auth.uid()') is null
      or to_regprocedure('stabilis.role_in_org(uuid)') is null
      or to_regprocedure('stabilis.can_access_location(uuid,uuid)') is null then
    raise exception 'Verify the Auth, membership role and location grant functions';
  end if;
  if not exists (select from pg_roles where rolname='anon')
      or not exists (select from pg_roles where rolname='authenticated') then
    raise exception 'Supabase client roles are unavailable';
  end if;
  if to_regclass('storage.buckets') is null or to_regclass('storage.objects') is null
      or to_regprocedure('storage.allow_any_operation(text[])') is null then
    raise exception 'Operation-aware Storage is unavailable';
  end if;
  if not exists (select from pg_class where oid=to_regclass('storage.objects') and relrowsecurity)
      or not exists (select from storage.buckets where id='stabilis-raw' and not public) then
    raise exception 'The raw bucket must be private and Storage objects must enforce RLS';
  end if;
end
$$;

select jsonb_build_object(
  'foundation', 'structural checks passed',
  'weekly_reviews', to_regclass('stabilis.weekly_labor_reviews') is not null,
  'weekly_audit', to_regclass('stabilis.weekly_labor_audit') is not null,
  'weekly_source_registry', to_regclass('stabilis.weekly_labor_source_files') is not null,
  'weekly_source_history', to_regprocedure('public.stabilis_weekly_source_history(uuid,uuid,uuid)') is not null
);
commit;
