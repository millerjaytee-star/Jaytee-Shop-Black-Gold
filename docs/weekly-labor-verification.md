# Weekly labor review verification

## Starting revisions

| Surface | Verified state on November 20, 2026 |
| --- | --- |
| Production | Netlify deploy `6ab7ba682718cb0008b4a432`, ready and published September 26, 2026, from `main` at `565fbd3ae5ea2abb5d0ef942c9e5b23eef16f588`. [Production](https://stabilis-ops-group.netlify.app/) · [Deploy](https://app.netlify.com/projects/stabilis-ops-group/deploys/6ab7ba682718cb0008b4a432) |
| Starting draft PR #14 | `feature/stabilis-weekly-review-20261120` at `7293f6870f86a943079262d7f2f9f0f81e1692e8`. Netlify deploy `6b00cc08abe0ae40a1a8763d` was ready. Open PRs #7 and #9 covered AI telemetry and a local intelligence prototype. [PR #14](https://github.com/millerjaytee-star/Jaytee-Shop-Black-Gold/pull/14) · [Deploy](https://app.netlify.com/projects/stabilis-ops-group/deploys/6b00cc08abe0ae40a1a8763d) |
| Dedicated backend | Supabase returned `INACTIVE` for Stabilis Operator Intelligence in `us-east-2`. The controlled-pilot gate applies to the dedicated environment and its documented scope. [Release gate](security-release-gate.md) |

## Offer and evidence before this branch

| Requirement | Published production | Starting PR #14 preview and proof |
| --- | --- | --- |
| Diagnostic name, fee and scope | The homepage presented a broad 14-day margin diagnostic without stating the fee. `/reset` and the confirmation page referred to an earlier $500 diagnostic. | The homepage presented the 14-Day Margin Recovery Diagnostic at $1,500 fixed for one agreed location. The start and scope details used the signed scope, cleared payment, ready records and agreed date. `/reset` positioned 30-day implementation as separately scoped. [Home](https://deploy-preview-14--stabilis-ops-group.netlify.app/#pilot) · [Reset](https://deploy-preview-14--stabilis-ops-group.netlify.app/reset) |
| Call length, confirmation and booking | Home used “Book a Margin Recovery Review” and included earlier 30-minute call copy. Production `/resources` and the confirmation source directed prospects to a 15-minute Calendly event. | The fit-call form requested 20 minutes and the confirmation named Jaytee as the email follow-up. A confirmed meeting requires a calendar invitation. A 20-minute booking event could not be verified. Netlify lists `stabilis-pilot` with `bot-field`, `name`, `email`, `company`, `locations` and `problem`, alongside the older `stabilis-lead` form. [Fit-call form](https://deploy-preview-14--stabilis-ops-group.netlify.app/#diagnostic) · [Confirmation](https://deploy-preview-14--stabilis-ops-group.netlify.app/thanks) |
| Buyer and territory | The form offered 3–10 and 11–25 as adjacent choices under a 3–15-location heading. The homepage did not list the territory. | The preview named restaurant, café and bakery groups with 3–15 sites in Washington, DC, Maryland and Northern Virginia. The form had an exact 3–15 option. [Home and form](https://deploy-preview-14--stabilis-ops-group.netlify.app/) |
| Free assessment and sample tools | Profit Leak Score™, Harbor & Hearth, sample report, Proof Ledger and sign-in were available. | The home explained that a higher Profit Leak Score™ means stronger operating controls and made the weekly demo, sample report, Proof Ledger, Control Room and client login reachable. [Home](https://deploy-preview-14--stabilis-ops-group.netlify.app/) |
| Evidence labels | Harbor & Hearth showed ten fictional locations, $392,570.56 modeled opportunity and $0 Verified Value. | The weekly review labeled $450 historical variance. A hosted browser run assigned an action, accepted it as the GM, submitted fictional completion evidence and saved the next week. Reload showed $125 following-week variance, $325 observed change and $0 client-verified impact. [Weekly review](https://deploy-preview-14--stabilis-ops-group.netlify.app/labor-review) · [Proof Ledger](https://deploy-preview-14--stabilis-ops-group.netlify.app/proof-ledger) |

The November 20 founder brief governs the current public offer. The dated Notion master build and offer history document earlier positioning and the deterministic calculation, human review and closed-loop evidence requirements. This review found no later explicit pricing decision in the sources it could read. The five personal Library file links had no accessible file content in this environment. Signed client scope governs each engagement. [Product workflow](operator-intelligence-v1.md) · [Release gate](security-release-gate.md)

## Run it locally

Run this command from the repository root with Python 3.11 or later.

```bash
python3 operator-intelligence/scripts/preview_site.py --port 8941
```

Open [the home page](http://127.0.0.1:8941/) or [the weekly labor review](http://127.0.0.1:8941/labor-review). The command returned HTTP 200 for `/`, `/labor-review`, `/login`, `/resources`, `/reset` and `/thanks`. Netlify processes hosted form submissions, and private customer sign-in and persistence require the active backend and applicable migration. The anonymous fictional walkthrough saves progress in the browser.

## Review changes and proof

| Source requirement | Existing behavior in PR #14 | Change | Verification |
| --- | --- | --- | --- |
| Phone-first entry, consistent offer and request receipt | Preview introduced the pilot and form. Call and fee copy were maintained in each page, and sign-in was in the collapsed menu on phones. | Direct phone login, plain-English labor question, canonical offer and terms, native Netlify form confirmation with founder follow-up, and a warm visual system across public and workspace routes. | Founding-offer contract, native-form browser test with an intercepted response, phone/tablet/widescreen route and layout checks, keyboard and JavaScript-disabled checks. |
| Source reports, mapping and weekly math | Three-file CSV/XLSX reconciler saved aggregate inputs and source descriptions. The general Data workspace separately handled private raw upload. | Retained the reconciler, added mismatch and coverage checks, linked the private intake, and made corrections return to analyst review with an audit record. The canonical fictional week supplies the chart, review and exports. | XLSX worksheet mapping, actual-dollar equations, short sales, expensive schedule, missing forecast, zero sales and changing rates. |
| Human approvals and manager follow-through | One weekly record supported release, action and a following-week comparison. | Stable links across sign-in, target and evidence instructions, due and review dates, clarification, version checks and mobile workspace navigation. | Real PostgreSQL procedures with synthetic analyst, owner, GMs, viewer and separate-tenant identity. Browser refresh and fresh sign-in retrieved the same review. |
| Comparable results, evidence labels and Ask Stabilis | Weekly comparison separated observed change and finance approval. Four analyst labels opened one workbench. | Separate mapping, diagnostic, verification and customer setup views. Weekly results and printable review retain separate evidence fields. Ask Stabilis cites released weekly records from the selected location and uses the stored deterministic metrics. | Browser verification of distinct queues, evidence note and record links. Server tests for a worsened/incomparable week, duplicate verification, cross-tenant and read-only checks, and concurrent writes. Ask handler tests with an isolated service transport. |
| Browser-local tools and private pilot validation | Control Room had long-standing local form and mobile issues. Historical pipeline notes mixed intended work and proof. | Kept the existing storage format and local tools. Added a founder-private pilot log outline with operational timing, engagement events and first-month research targets. | Browser tests of Control Room inputs, CSV, snapshots and exports. No real interview, payment, operator comparison or business outcome is recorded in this build. |

### Fictional operator files

- `assets/labor-review-example.csv` and `assets/labor-examples/following-week.csv` carry the public review baseline and comparison.
- `assets/labor-examples/weekly-reports.xlsx` and the three daily CSV exports in that directory exercise mapping as a separate fictional intake week with the same baseline totals.
- Baseline forecast and actual sales are $10,000 and $9,000. Scheduled and paid labor are 125 hours/$2,500 and 135 hours/$2,700. At 25%, actual labor was 30%, five percentage points over target. The $450 historical variance is $0 from the schedule, $250 from the sales miss and $200 from payroll above schedule.
- The following week uses $9,500 actual sales and 125 paid hours/$2,500. The variance is $125 and the observed change is $325. The fictional portfolio contains ten locations, $392,570.56 modeled opportunity and $0 Verified Value. HHR-07 overtime contributes $0 additional to the rollup.

### Scope still to validate

The new deploy preview and loopback server use a public-only browser configuration. Private browser verification uses PostgreSQL 17 and an isolated auth/REST test transport. The dedicated Stabilis Supabase project is inactive. Hosted sign-in, password recovery, live grant/schema preflight, deployment of the updated migration, private storage and report delivery require the authorized staging rehearsal before customer release.

Weekly mapping persists the confirmed aggregates, coverage and source references. Original reports can go through the existing private intake subject to signed storage and retention terms. The weekly UI does not create a managed association to a private raw file, preserve role/daypart fact series, or automate promotion of a finding into a signed diagnostic readout or 90-day roadmap. An analyst can use the linked review and inventory evidence in the existing diagnostic process.

The fit-call form kept its registered Netlify name and fields. Hosted receipt and notification delivery were not exercised with a live submission. A working 20-minute booking event has not been verified. Real sessions, operator interviews, cleared payments, comparison with an operator’s existing tool, repeat use and release approval require real evidence or authorization.
