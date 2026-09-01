# Security Release Gate

**REAL FINANCIAL DATA RELEASE GATE = BLOCKED**

Real restaurant financial data is prohibited until every item below is demonstrated against the dedicated Stabilis Supabase project:

- [ ] migrations applied in order
- [ ] RLS enabled on every exposed tenant table
- [ ] Customer A cannot read Customer B
- [ ] Customer A cannot modify Customer B
- [ ] anonymous users cannot access private tenant rows
- [ ] location-restricted roles cannot read unassigned locations
- [ ] analyst/admin access follows explicit role rules
- [ ] `stabilis-raw`, `stabilis-reports` and `stabilis-evidence` buckets are private
- [ ] cross-tenant storage reads/writes fail
- [ ] signed/private file access works for authorized users only
- [ ] generated reports cannot leak between tenants
- [ ] service-role credentials are absent from browser/public Netlify variables
- [ ] login/logout/reset/invite/protected route behavior is validated
- [ ] API authorization rejects cross-tenant identifiers
- [ ] PostgreSQL/Auth/Storage/API logs reviewed without raw financial-data leakage
- [ ] Supabase security advisor reviewed and remediated
- [ ] performance advisor reviewed for material issues
- [ ] HHR-07 deduplication regression remains green at $392,570.56

The public Harbor & Hearth demo may remain available because it contains only fictional data.
