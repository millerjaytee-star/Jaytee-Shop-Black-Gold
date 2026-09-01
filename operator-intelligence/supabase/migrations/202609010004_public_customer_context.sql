-- Stabilis Operator Intelligence — authenticated customer context
-- Browser-visible tenant context is intentionally limited to these public views.
-- The custom stabilis schema itself remains unexposed through PostgREST.

create or replace view public.stabilis_my_organizations
with (security_invoker = true)
as
select o.id,
       o.name,
       o.slug,
       m.role::text as role,
       m.id as membership_id
from stabilis.memberships m
join stabilis.organizations o on o.id = m.organization_id
where m.profile_id = auth.uid()
  and m.status = 'ACTIVE';

create or replace view public.stabilis_my_locations
with (security_invoker = true)
as
select l.id,
       l.organization_id,
       l.code,
       l.name,
       l.market,
       l.region,
       l.timezone,
       l.service_model
from stabilis.locations l
where stabilis.can_access_location(l.organization_id, l.id);

revoke all on public.stabilis_my_organizations from public, anon;
revoke all on public.stabilis_my_locations from public, anon;
grant select on public.stabilis_my_organizations to authenticated;
grant select on public.stabilis_my_locations to authenticated;

comment on view public.stabilis_my_organizations is
  'Authenticated Stabilis tenant context. Security-invoker view; underlying stabilis RLS remains authoritative.';
comment on view public.stabilis_my_locations is
  'Authenticated Stabilis location context. Security-invoker view; underlying stabilis RLS and can_access_location remain authoritative.';
