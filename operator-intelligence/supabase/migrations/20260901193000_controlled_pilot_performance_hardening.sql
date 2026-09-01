-- Controlled-pilot performance hardening after release-candidate advisor pass.
create index if not exists insight_feedback_finding_idx on stabilis.insight_feedback(finding_id) where finding_id is not null;
create index if not exists insight_feedback_recommendation_idx on stabilis.insight_feedback(recommendation_id) where recommendation_id is not null;
create index if not exists insight_feedback_profile_idx on stabilis.insight_feedback(profile_id);
create index if not exists notification_preferences_profile_idx on stabilis.notification_preferences(profile_id);
create index if not exists onboarding_progress_updated_by_idx on stabilis.onboarding_progress(updated_by) where updated_by is not null;
create index if not exists operator_notes_author_idx on stabilis.operator_notes(author_id);
create index if not exists operator_notes_location_idx on stabilis.operator_notes(location_id) where location_id is not null;
create index if not exists pilot_accounts_analyst_owner_idx on stabilis.pilot_accounts(analyst_owner) where analyst_owner is not null;
create index if not exists usage_events_profile_idx on stabilis.usage_events(profile_id);

drop policy if exists pilot_read on stabilis.pilot_accounts;
drop policy if exists pilot_write on stabilis.pilot_accounts;
drop policy if exists pilot_insert on stabilis.pilot_accounts;
drop policy if exists pilot_update on stabilis.pilot_accounts;
drop policy if exists pilot_delete on stabilis.pilot_accounts;
create policy pilot_read on stabilis.pilot_accounts for select to authenticated using (stabilis.is_member(organization_id));
create policy pilot_insert on stabilis.pilot_accounts for insert to authenticated with check (stabilis.is_internal_reviewer(organization_id));
create policy pilot_update on stabilis.pilot_accounts for update to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));
create policy pilot_delete on stabilis.pilot_accounts for delete to authenticated using (stabilis.is_internal_reviewer(organization_id));

drop policy if exists onboarding_read on stabilis.onboarding_progress;
drop policy if exists onboarding_write on stabilis.onboarding_progress;
drop policy if exists onboarding_insert on stabilis.onboarding_progress;
drop policy if exists onboarding_update on stabilis.onboarding_progress;
drop policy if exists onboarding_delete on stabilis.onboarding_progress;
create policy onboarding_read on stabilis.onboarding_progress for select to authenticated using (stabilis.is_member(organization_id));
create policy onboarding_insert on stabilis.onboarding_progress for insert to authenticated with check (stabilis.can_write_org(organization_id));
create policy onboarding_update on stabilis.onboarding_progress for update to authenticated using (stabilis.can_write_org(organization_id)) with check (stabilis.can_write_org(organization_id));
create policy onboarding_delete on stabilis.onboarding_progress for delete to authenticated using (stabilis.can_write_org(organization_id));

drop policy if exists feedback_read on stabilis.insight_feedback;
drop policy if exists feedback_insert on stabilis.insight_feedback;
create policy feedback_read on stabilis.insight_feedback for select to authenticated using (stabilis.is_member(organization_id));
create policy feedback_insert on stabilis.insight_feedback for insert to authenticated with check (profile_id=(select auth.uid()) and stabilis.is_member(organization_id));

drop policy if exists notes_read on stabilis.operator_notes;
drop policy if exists notes_insert on stabilis.operator_notes;
drop policy if exists notes_delete on stabilis.operator_notes;
create policy notes_read on stabilis.operator_notes for select to authenticated using (stabilis.is_member(organization_id) and (location_id is null or stabilis.can_access_location(organization_id, location_id)));
create policy notes_insert on stabilis.operator_notes for insert to authenticated with check (author_id=(select auth.uid()) and stabilis.can_write_org(organization_id) and (location_id is null or stabilis.can_access_location(organization_id, location_id)));
create policy notes_delete on stabilis.operator_notes for delete to authenticated using (author_id=(select auth.uid()) or stabilis.is_internal_reviewer(organization_id));

drop policy if exists usage_insert on stabilis.usage_events;
drop policy if exists usage_read on stabilis.usage_events;
create policy usage_insert on stabilis.usage_events for insert to authenticated with check (profile_id=(select auth.uid()) and stabilis.is_member(organization_id));
create policy usage_read on stabilis.usage_events for select to authenticated using (stabilis.is_internal_reviewer(organization_id));

drop policy if exists notification_self on stabilis.notification_preferences;
create policy notification_self on stabilis.notification_preferences for all to authenticated using (profile_id=(select auth.uid()) and stabilis.is_member(organization_id)) with check (profile_id=(select auth.uid()) and stabilis.is_member(organization_id));
