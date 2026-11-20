# Stabilis Ops Group + Stabilis Operator Intelligence™

One maintainable Stabilis product combining the public website, Profit Leak Score™, fictional Operator Intelligence demo, customer authentication shell, deterministic intelligence engine, analyst-review controls, secure multi-tenant data architecture, action tracking, results/Verified Value, reports, GitHub, Netlify and Supabase.

## Product promise

Stabilis is an operating intelligence system for multi-unit businesses. We identify where you're losing money, quantify the opportunity, tell your team what to fix, and track whether it actually gets fixed.

**Stabilize. Systemize. Scale.**

## Production surfaces

- Public website: `https://stabilis-ops-group.netlify.app`
- Operator Intelligence demo: `/operator-intelligence`
- Sample report: `/operator-intelligence-report`
- Login: `/login`
- Protected shell: `/app`

Harbor & Hearth is fictional demo data. Its controlled modeled recoverable opportunity is **$392,570.56**. This is not realized or guaranteed savings. Verified Value starts separately at $0 in the demo.

## Architecture

Public Netlify site -> Supabase Auth -> tenant-aware app -> private Stabilis Supabase -> deterministic calculation/validation engine -> analyst review -> customer outputs -> actions -> observed results -> Verified Value.

AI may synthesize and explain already-calculated authorized facts. It must not invent financial truth, bypass authorization, modify raw facts silently, or mark its own value VERIFIED.

## Supabase

Dedicated project: `Stabilis Operator Intelligence` / `vpunfmwklwjefvchvmpn` / `us-east-2`.

Live negative-security tests passed for cross-tenant reads, cross-tenant writes, anonymous schema access, private storage isolation and released-report isolation. Current Supabase security advisor reports zero security lints after hardening.

The authoritative real-financial-data release decision is maintained in [`docs/security-release-gate.md`](docs/security-release-gate.md). Its current status is **CONTROLLED PILOT FINANCIAL DATA RELEASE GATE = PASSED** for the dedicated Stabilis environment and controlled-pilot scope described there. This does not approve unrelated environments or remove the remaining calibration and customer-value validation work.

## Quality gate

The GitHub workflow regenerates deterministic Harbor & Hearth fixtures, runs pytest, compiles Python, runs Ruff and type-checks the financial/security core with mypy. The HHR-07 overtime duplicate-count regression must remain protected; canonical demo opportunity = **$392,570.56**.

## Local engine

```bash
cd operator-intelligence
python scripts/generate_dataset.py
pytest -q
python scripts/run_analysis.py
```

See `docs/architecture.md`, `docs/database.md`, `docs/intelligence-engine.md`, `docs/security-release-gate.md`, `docs/operator-intelligence-v1.md`, and `docs/deployment.md`.

## Weekly labor review

From the repository root, run `python3 operator-intelligence/scripts/preview_site.py --port 8080`, then open `http://127.0.0.1:8080/`. The public walkthrough is at `/labor-review`. It uses fictional information and saves changes in that browser. Client work opens at `/app#labor-review` and requires a real assigned organization and location.

- **Jaytee:** Open the public homepage, try the labor review and follow the fit-call form. The 14-Day Margin Recovery Diagnostic is $1,500 for one agreed location. Update the shared offer in `scripts/sync-founding-offer.mjs` and run `node scripts/sync-founding-offer.mjs` to regenerate the pre-rendered copy.
- **Owner:** Open the fictional review for Juniper Café, inspect the $450 overage, choose the manager and approve the action. Week 1 has $250 attributable to lower sales and $200 attributable to payroll above schedule.
- **GM:** Switch the demo role to General manager, accept the assignment and submit evidence. Authenticated users receive their assigned role from their membership.
- **Owner or analyst:** Compare the second week, record whether the periods are comparable, and print the review. Using the example inputs, variance falls to $125, an observed improvement of $325. Verified Value remains $0 until documented client finance validation.
- **Analyst:** Open a new review to inspect intake and release. Source references, corrections, review state and history accompany the underlying weekly totals.

The public walkthrough runs on Netlify without Supabase. Deploy previews and the loopback server use a public-only browser configuration. Private testing uses isolated synthetic roles and a test transport. Customer release requires an active dedicated Stabilis backend, a reviewed migration rehearsal and validation against existing tenant and location grants. Netlify handles the hosted fit-call form. The loopback preview serves the pages and does not process a real submission.

Synthetic source files and worksheet mapping are in `assets/labor-examples/` and on the public review. The files contain fictional aggregates. Build the same static publish directory as Netlify with `python3 operator-intelligence/scripts/build_site.py`. Repository documentation, migrations, tests and generated engine records stay outside that directory. See the [verification handoff](docs/weekly-labor-verification.md) for the deployment baseline and test scope.

The optional production AI readiness probe uses a private `STABILIS_AI_HEALTH_SECRET` shared by the Netlify production function and the GitHub Actions production job. Configure a fresh value if that probe is needed. The preview checks unauthenticated behavior without running a billable model request.
