alter table stabilis.intelligence_queries
  add column if not exists query_fingerprint text,
  add column if not exists question_chars integer,
  add column if not exists prompt_version text,
  add column if not exists context_builder_version text,
  add column if not exists output_schema_version text,
  add column if not exists evaluation_version text,
  add column if not exists input_tokens integer,
  add column if not exists cached_input_tokens integer,
  add column if not exists output_tokens integer,
  add column if not exists estimated_cost_usd numeric(14,8),
  add column if not exists cost_basis text;

create index if not exists intelligence_queries_model_created_idx
  on stabilis.intelligence_queries(organization_id,model_name,created_at desc);

create index if not exists intelligence_queries_fingerprint_created_idx
  on stabilis.intelligence_queries(organization_id,query_fingerprint,created_at desc)
  where query_fingerprint is not null;
