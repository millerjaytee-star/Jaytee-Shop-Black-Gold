# Database

The canonical database is PostgreSQL/Supabase under the `stabilis` schema.

Core domains include identity/tenancy, operating structure, ingestion/mapping/validation, normalized financial/operating facts, intelligence, execution/results, reporting and audit/system events.

All schema changes are migrations. UUIDs are used for primary keys. Important outputs preserve calculation/model version and provenance.

## Deduplication contract
Canonical enterprise opportunity rollups count only `PRIMARY` opportunities where `counted_in_rollup=true`. Supporting evidence is retained but excluded from financial rollup. A partial unique index prevents more than one counted primary record for the same canonical opportunity ID.

The Harbor & Hearth regression target is **$392,570.56**. The former **$416,284.30** value is invalid because HHR-07 overtime was double counted.

## RLS philosophy
RLS is the database authorization backstop. Customer access requires explicit active organization membership and, for restricted roles, location assignment. Analyst/admin access follows explicit roles; public demo routes never query real tenant tables.
