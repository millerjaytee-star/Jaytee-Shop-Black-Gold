# Stabilis Security Release Gate

Status updated 2026-09-01.

## Passed live infrastructure controls

- Dedicated Supabase project: `Stabilis Operator Intelligence` (`vpunfmwklwjefvchvmpn`, `us-east-2`).
- Stabilis tenant tables use Row Level Security.
- Cross-tenant read test: Org A could see 1 own organization and 0 Org B organizations/locations.
- Cross-tenant write test: Org A changed 0 Org B rows.
- Anonymous role has no USAGE privilege on the `stabilis` schema.
- Private raw storage test: own-tenant insert succeeded; cross-tenant insert was denied by RLS.
- Released-report isolation test: Org A could see 1 own report and 0 Org B reports.
- `stabilis-raw`, `stabilis-reports`, and `stabilis-evidence` buckets are private.
- Supabase security advisor: 0 current security lints after hardening.
- Service-role credentials are not embedded in browser files.
- Canonical opportunity rollup counts only PRIMARY opportunities explicitly marked `counted_in_rollup`.
- HHR-07 overtime remains supporting evidence; the controlled canonical modeled opportunity stays $392,570.56.

## Still required before real restaurant financial uploads

- Complete a positive-path Supabase Auth test using a real invited test user: login, session refresh, logout, forgot/reset password, protected-route redirect and organization membership navigation.
- Complete the invitation acceptance workflow end to end.
- Repeat the protected application smoke test in production after the final GitHub merge and Netlify deploy.

## Gate

**REAL FINANCIAL DATA RELEASE GATE = BLOCKED**

The database/storage tenant isolation layer passed the live negative-security tests. The gate stays blocked until the positive authentication/invitation workflow above is exercised end to end. Fictional Harbor & Hearth demo data is permitted.
