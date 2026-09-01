# Stabilis Security Release Gate

Status updated 2026-09-01.

## Passed live infrastructure controls

- Dedicated Supabase project: `Stabilis Operator Intelligence` (`vpunfmwklwjefvchvmpn`, `us-east-2`).
- Stabilis tenant tables use Row Level Security.
- Cross-tenant read test: Org A could see its own organization and no Org B organizations/locations.
- Cross-tenant write test: Org A changed 0 Org B rows.
- Anonymous role has no USAGE privilege on the `stabilis` schema.
- The custom `stabilis` schema remains unexposed through PostgREST; browser tenant context is limited to security-invoker public views.
- Anonymous access to `public.stabilis_my_organizations` is denied.
- Private raw storage test: own-tenant insert succeeded; cross-tenant insert was denied by RLS.
- Released-report isolation test: Org A could see its own released report and no Org B report.
- `stabilis-raw`, `stabilis-reports`, and `stabilis-evidence` buckets are private.
- Supabase security advisor: 0 current security lints after hardening.
- Service-role credentials are not embedded in browser files.
- Canonical opportunity rollup counts only PRIMARY opportunities explicitly marked `counted_in_rollup`.
- HHR-07 overtime remains supporting evidence; the controlled canonical modeled opportunity stays $392,570.56.

## Passed live authentication and tenant-context controls

A temporary, synthetic release-smoke workflow was run against the live dedicated Supabase project and then cleaned up.

- Confirmed-user creation: PASS.
- Password sign-in: PASS.
- Authenticated `/user` session verification: PASS.
- Session refresh using the refresh token: PASS; the refreshed session remained valid.
- Logout: PASS.
- Password recovery link generation: PASS.
- Password recovery session: PASS.
- Password update followed by sign-in with the new password: PASS.
- Invitation link generation for a separate fresh identity: PASS.
- Invitation acceptance session: PASS.
- Active organization membership resolution: PASS.
- Authorized location navigation: PASS (2 assigned locations returned).
- Direct cross-tenant organization-ID guess: PASS (0 records returned).
- Membership remained available after token refresh: PASS.
- Temporary QA users and tenant data: REMOVED.
- Temporary smoke endpoints: LOCKED with JWT verification and disabled response bodies.

## Production web controls

- Netlify production deploy after PR #3 merge: READY.
- `/`, `/operator-intelligence`, `/operator-intelligence-report`, `/login`, `/app`, and `/stabilis-config.js` returned HTTP 200 in live production smoke checks.
- `/app` contains no customer financial truth in static HTML. It requires a valid Supabase session before tenant data is fetched.
- `/app` accepts verified invitation/session fragments, stores the session only in `sessionStorage`, refreshes expiring sessions, and resolves only RLS-scoped organization/location context.
- `/login` supports password sign-in, reset-email request, verified recovery-link handling, new-password update, and handoff into the secure application.

## Gate

**CONTROLLED PILOT FINANCIAL DATA RELEASE GATE = PASSED**

Stabilis Operator Intelligence is approved for controlled restaurant pilots using the dedicated Stabilis environment, tenant-scoped authentication, private storage, deterministic calculations, analyst review, and release controls.

This is an infrastructure/security/authentication release decision, not a claim of real-world model calibration, customer value validation, or product-market fit. Those remain pilot-stage validation activities. Harbor & Hearth remains fictional demonstration data, and the $392,570.56 figure is modeled recoverable opportunity from the synthetic controlled fixture—not verified savings.
