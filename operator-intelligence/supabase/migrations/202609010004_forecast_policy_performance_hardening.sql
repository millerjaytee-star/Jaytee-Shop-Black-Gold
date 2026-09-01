-- Performance hardening for forecast and command-center tables.
create index if not exists forecast_accuracy_location_idx on stabilis.forecast_accuracy(location_id);
create index if not exists forecast_inputs_run_idx on stabilis.forecast_inputs(forecast_run_id);
create index if not exists forecast_inputs_location_idx on stabilis.forecast_inputs(location_id);
create index if not exists forecast_inputs_org_idx on stabilis.forecast_inputs(organization_id);
create index if not exists forecast_inputs_source_file_idx on stabilis.forecast_inputs(source_file_id);
create index if not exists forecast_models_created_by_idx on stabilis.forecast_models(created_by);
create index if not exists forecast_runs_created_by_idx on stabilis.forecast_runs(created_by);
create index if not exists forecast_runs_model_idx on stabilis.forecast_runs(model_id);
create index if not exists forecast_values_location_idx on stabilis.forecast_values(location_id);
create index if not exists user_preferences_profile_idx on stabilis.user_preferences(profile_id);
create index if not exists widget_preferences_profile_idx on stabilis.widget_preferences(profile_id);

drop policy if exists forecast_models_write on stabilis.forecast_models;
drop policy if exists forecast_models_insert on stabilis.forecast_models;
drop policy if exists forecast_models_update on stabilis.forecast_models;
drop policy if exists forecast_models_delete on stabilis.forecast_models;
create policy forecast_models_insert on stabilis.forecast_models for insert to authenticated with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_models_update on stabilis.forecast_models for update to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_models_delete on stabilis.forecast_models for delete to authenticated using (stabilis.is_internal_reviewer(organization_id));

drop policy if exists forecast_runs_write on stabilis.forecast_runs;
drop policy if exists forecast_runs_insert on stabilis.forecast_runs;
drop policy if exists forecast_runs_update on stabilis.forecast_runs;
drop policy if exists forecast_runs_delete on stabilis.forecast_runs;
create policy forecast_runs_insert on stabilis.forecast_runs for insert to authenticated with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_runs_update on stabilis.forecast_runs for update to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_runs_delete on stabilis.forecast_runs for delete to authenticated using (stabilis.is_internal_reviewer(organization_id));

drop policy if exists forecast_inputs_write on stabilis.forecast_inputs;
drop policy if exists forecast_inputs_insert on stabilis.forecast_inputs;
drop policy if exists forecast_inputs_update on stabilis.forecast_inputs;
drop policy if exists forecast_inputs_delete on stabilis.forecast_inputs;
create policy forecast_inputs_insert on stabilis.forecast_inputs for insert to authenticated with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_inputs_update on stabilis.forecast_inputs for update to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_inputs_delete on stabilis.forecast_inputs for delete to authenticated using (stabilis.is_internal_reviewer(organization_id));

drop policy if exists forecast_values_write on stabilis.forecast_values;
drop policy if exists forecast_values_insert on stabilis.forecast_values;
drop policy if exists forecast_values_update on stabilis.forecast_values;
drop policy if exists forecast_values_delete on stabilis.forecast_values;
create policy forecast_values_insert on stabilis.forecast_values for insert to authenticated with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_values_update on stabilis.forecast_values for update to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_values_delete on stabilis.forecast_values for delete to authenticated using (stabilis.is_internal_reviewer(organization_id));

drop policy if exists forecast_accuracy_write on stabilis.forecast_accuracy;
drop policy if exists forecast_accuracy_insert on stabilis.forecast_accuracy;
drop policy if exists forecast_accuracy_update on stabilis.forecast_accuracy;
drop policy if exists forecast_accuracy_delete on stabilis.forecast_accuracy;
create policy forecast_accuracy_insert on stabilis.forecast_accuracy for insert to authenticated with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_accuracy_update on stabilis.forecast_accuracy for update to authenticated using (stabilis.is_internal_reviewer(organization_id)) with check (stabilis.is_internal_reviewer(organization_id));
create policy forecast_accuracy_delete on stabilis.forecast_accuracy for delete to authenticated using (stabilis.is_internal_reviewer(organization_id));
