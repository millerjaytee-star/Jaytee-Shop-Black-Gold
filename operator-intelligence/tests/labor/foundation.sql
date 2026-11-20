-- Synthetic fixtures for an isolated PostgreSQL instance. This is not a deployable Stabilis foundation.
create schema stabilis;
create schema auth;
create role authenticated;
create role anon;
create function auth.uid() returns uuid language sql stable as
  $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
create table stabilis.organizations(id uuid primary key);
create table stabilis.locations(id uuid primary key,organization_id uuid not null references stabilis.organizations(id),timezone text default 'America/New_York');
create table stabilis.profiles(id uuid primary key);
create table stabilis.memberships(id uuid primary key default gen_random_uuid(),organization_id uuid,profile_id uuid,role text,status text);
create table stabilis.membership_locations(membership_id uuid references stabilis.memberships(id), location_id uuid references stabilis.locations(id), primary key(membership_id,location_id));
create function stabilis.role_in_org(org uuid) returns text language sql stable as
  $$ select role from stabilis.memberships where organization_id=org and profile_id=auth.uid() and status='ACTIVE' $$;
create function stabilis.can_access_location(org uuid,loc uuid) returns boolean language sql stable as
  $$ select coalesce(stabilis.role_in_org(org) in ('STABILIS_ADMIN','STABILIS_ANALYST','OWNER_EXECUTIVE')
    or exists(select 1 from stabilis.membership_locations g join stabilis.memberships m on m.id=g.membership_id where m.profile_id=auth.uid() and m.organization_id=org and g.location_id=loc),false) $$;
