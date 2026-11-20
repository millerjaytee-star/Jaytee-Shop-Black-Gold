-- Synthetic fixtures for an isolated PostgreSQL instance. This is not a deployable Stabilis foundation.
create schema stabilis;
create schema auth;
create role authenticated;
create role anon;
create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
create table stabilis.organizations(id uuid primary key);
create table stabilis.locations(id uuid primary key,organization_id uuid not null references stabilis.organizations(id));
create table stabilis.profiles(id uuid primary key);
create table stabilis.memberships(organization_id uuid,profile_id uuid,role text,status text);
create table stabilis.test_location_grants(profile_id uuid,location_id uuid);
create function stabilis.role_in_org(org uuid) returns text language sql stable as
  $$ select role from stabilis.memberships where organization_id=org and profile_id=auth.uid() and status='ACTIVE' $$;
create function stabilis.can_access_location(org uuid,loc uuid) returns boolean language sql stable as
  $$ select coalesce(stabilis.role_in_org(org) in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE')
    or exists(select 1 from stabilis.test_location_grants where profile_id=auth.uid() and location_id=loc),false) $$;
