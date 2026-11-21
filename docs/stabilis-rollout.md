# Stabilis rollout and release gates

## One production release

PR #15 contains PR #14's reviewed web work in its ancestry. Keep both drafts open as review references. After hosted staging and approval, deploy the reviewed head of #15 through one approved merge to main. PR #14 can then be marked superseded. If the web work needs an earlier separate release, merge #14 once, reconcile #15 against the new main, and verify only the outstanding changes before separately approving #15. Do not merge both drafts for the same release.

Record the production Git commit and Netlify deploy ID and the staging Git commit, project reference, build number and test date. A Netlify preview can demonstrate fictional records and public routing. Its default build intentionally has no customer backend.

## Rehearse the target

1. Identify a separate authorized staging web site and Supabase project. Use synthetic identities and source files. Read the actual Auth settings, invitation flow, RLS grants, role mappings, private Storage policies, and migration ledger. The repository's synthetic foundation deliberately stands in for some historic managed schema. Start an isolated hosted rehearsal from an approved schema-only copy of that foundation. Leave customer data and files behind.
2. Run the read-only structural preflight under an authorized administrative database connection. Run synthetic role checks against the scoped views and RLS as separate tests.

   ```sh
   psql -X -v ON_ERROR_STOP=1 -f operator-intelligence/scripts/weekly_release_preflight.sql
   ```

   Set the database connection through the approved libpq service or environment mechanism. Reconcile any pre-existing migration objects with the target ledger before applying new SQL. Mixed present and missing components need investigation. A passing structural check gives no evidence about a role's effective access.

3. Confirm restore procedures and a recoverable backup for the approved target. Apply `20261120220000_weekly_labor_review.sql` before `20261120231842_weekly_labor_source_archive.sql` through the approved migration process. Verify each transaction, its migration ledger entry, and the resulting grants before continuing. Audit existing migrations and the actual environment schema before pushing a full history.
4. Build the isolated static staging package using the approved stage origin and stage project's publishable key. Supply the optional Apple identifier only after the team confirms it. This package enables Auth only at the specified staging origin. Its static policies disable form submissions and exclude functions. Deploy from that directory to a separate authorized static host where its generated headers and redirects take effect. The repository's Netlify public preview and production build remain separate.

   ```sh
   cd operator-intelligence
   python3 -m scripts.build_staging_site
   ```

   Inputs are `STABILIS_STAGING_WEB_ORIGIN`, `STABILIS_STAGING_SUPABASE_URL`, `STABILIS_STAGING_SUPABASE_PUBLISHABLE_KEY` and optionally `STABILIS_STAGING_APPLE_APPLICATION_IDENTIFIER`. Output is `dist/staging` at the repository root. Serve `/login` on the same staging origin, and configure Auth recovery to that exact HTTPS route. Check the deployed Content Security Policy permits the approved API only, App and Login use no-store headers and the staged browser config becomes demo-only on a different origin. Leave lead and support forms outside this Auth staging deployment.

5. For the signed internal build, configure the same staging API and publishable key in the ignored Xcode settings. Set `STABILIS_WEB_ORIGIN` to the staging origin, `STABILIS_ASSOCIATED_DOMAIN` to its hostname and `STABILIS_RECOVERY_URL` to its `/login` route. Verify that Apple Associated Domains is enabled for the signed identifier. Test both installed-app and browser paths and confirm they still require matching grants. The app’s support and privacy links point to the public Stabilis site, which needs independently verified routing before submission. See the [Apple handoff](ios-app-store.md).
6. Run the [synthetic reviewer walkthrough](pilot-release-rehearsal.md). Confirm completed-week import, role gates, archive byte integrity, cleanup through the Storage API, and the expected $450 and $125 variances, $325 observed improvement, and $0 client-verified impact before finance approval. Keep separate evidence for the physical-device test and each hosted Auth and Storage check.

## Rollout and recovery

- **Backend owner** confirms the managed target, backup, current foundation, exact migration order, effective grants and both the pre- and post-migration smoke checks. A failed SQL transaction should leave its objects absent and its migration unrecorded. Verify that claim and repair the precondition before retrying. If a migration already committed, stop promotion, retain the data, and use an explicitly reviewed fix forward. Restore data only under the approved recovery plan.
- **Web owner** verifies the public offer, support contact and monitored replies, protected login and app routes, and link fallback. Release the reviewed web build only after founder approval. If a deployed client regresses, stop promotion and prepare a tested corrective deploy. Preserve source and customer records.
- **iOS release owner** verifies the signed app archive, stage config, device checks and exact build in TestFlight. Address review feedback with an incremented build and repeat the affected tests. Choose manual release to retain the publication decision.
- **Jaytee** approves the staging route if provisioning or spending is required, designates the monitored support contact, gives the release decisions separately, and authorizes operator participation and any real commercial activity.

## Gates

| Gate | Current evidence | Remaining action and owner |
| --- | --- | --- |
| Rehearsal and web integration | Tests and artifacts are linked from the draft PR. [Draft PR #15](https://github.com/millerjaytee-star/Jaytee-Shop-Black-Gold/pull/15) | Engineering reruns the latest suite for the exact commit selected for release. |
| Hosted staging foundation and permissions | Dedicated Stabilis Supabase project reports inactive, no listed branches, and migration history timed out. Dedicated synthetic staging is unverified. | Jaytee identifies an approved separate project or authorizes provisioning after a quote. Backend owner verifies actual Auth, grants and Storage. |
| Retention and recovery | Local PostgreSQL and Storage rehearsals provide synthetic evidence, while production retention is governed by signed scope. | Backend owner rehearses the target Storage deletion path and records actual deletion and any applicable backup retention. |
| Support and fit-call routing | Browser forms, payloads and receipts were exercised without hosted submission. [Forms rehearsal](support-release-rehearsal.md) | Jaytee approved stabilisopsgroup@gmail.com. Web owner verifies hosted destinations and performs controlled delivery and reply tests. |
| Signing and internal TestFlight | App Store Connect reached Apple Account sign-in. The last build and archive were unsigned. [Apple handoff](ios-app-store.md) | Account Holder verifies the Stabilis team, roles, App ID and agreements. iOS owner signs, verifies a physical device and uploads within authorization. |
| App Review, production and release | Draft listing and synthetic reviewer walkthrough are ready for review. | Jaytee approves submission, production changes and public release separately. |
| Operator validation | Script and private measurement schema prepared. [Pilot rehearsal](pilot-release-rehearsal.md) | Jaytee authorizes participation. Pilot owner records actual outcomes after participation and payment evidence after clearance. |
