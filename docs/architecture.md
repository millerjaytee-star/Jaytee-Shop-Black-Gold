# Architecture

## Product boundary
One Stabilis product combines a public Netlify marketing surface, a read-only fictional demo, an authenticated operator application, an internal analyst workbench, deterministic calculation services, Supabase/PostgreSQL, private storage, reporting and verified-result tracking.

## Runtime strategy
- **Netlify:** public site, lead capture, fictional demo and static report examples.
- **Supabase Auth/Postgres/Storage:** tenant identity, membership, canonical facts, intelligence records, actions, results, reports and private files.
- **FastAPI reference service:** controlled orchestration boundary for ingestion/analysis/report workflows where server-side logic is preferable to browser access. It can later be deployed to a suitable backend runtime without moving the static site off Netlify.
- **AI:** narrative/synthesis assistance only after authorization and deterministic calculations. AI never becomes the source of financial truth, tenant authorization, approval or verified value.

## Data flow
Upload → Detect → Map → Validate → Normalize → Store → Calculate → Benchmark → Detect → Diagnose → Quantify → Deduplicate → Prioritize → Analyst Review → Customer Intelligence → Action → Observed Result → Verification → Verified Value.

## Tenant model
Every private operating record is scoped to an organization and, when relevant, a location. Supabase RLS uses authenticated membership/location assignments. Service-role credentials remain server-side only.

## Environment separation
Local → development → deploy preview/staging → production. Fictional demo data is safe for public use. Real financial uploads remain disabled until the dedicated live Stabilis Supabase security gate passes.
