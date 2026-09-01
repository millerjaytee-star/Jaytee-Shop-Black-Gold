# Stabilis Ops Group — Operator Intelligence

Stabilis is an operating-intelligence and execution platform for multi-unit businesses, initially focused on restaurants. The public website, fictional Harbor & Hearth demo, deterministic intelligence engine, analyst review controls, Supabase schema/migrations and Netlify deployment live in this repository.

**Positioning:** Stabilize. Systemize. Scale.

**Product loop:** Data → Validate → Normalize → Calculate → Benchmark → Detect → Diagnose → Quantify → Prioritize → Review → Recommend → Assign → Execute → Verify → Measure → Learn.

## Repository structure

- `/index.html` — public Stabilis website and Profit Leak Score
- `/operator-intelligence.html` — read-only Harbor & Hearth demo command center
- `/operator-intelligence-report.html` — fictional Operator Intelligence Report v1 sample
- `/login.html` — secure-app gate; does not fake authentication before live RLS validation
- `/operator-intelligence/` — deterministic engine, application reference implementation, tests and Supabase migrations
- `/docs/` — architecture, database, intelligence, deployment and release-gate documentation

## Local quality gate

```bash
cd operator-intelligence
python -m pip install -e ".[test,dev]"
python scripts/generate_dataset.py
pytest -q
python -m compileall -q src scripts tests
ruff check src scripts tests
mypy src/application/security.py src/application/fiscal.py src/scoring/confidence.py src/scoring/priority.py src/metrics/engine.py
```

## Netlify

The production static experience is connected to `main` on the Netlify project `stabilis-ops-group`. Static assets publish from the repository root. The secure authenticated/data application must not be simulated in the browser; it activates only after the dedicated Stabilis Supabase project passes the release gate.

## Supabase

Apply migrations in order from `operator-intelligence/supabase/migrations/` to a **dedicated Stabilis Supabase project**. Never reuse Concrete Motivation, MarketIQ or another unrelated project's database for Stabilis customer financial data.

## Release safety

**REAL FINANCIAL DATA RELEASE GATE = BLOCKED** until live Supabase RLS, cross-tenant read/write, private storage, auth, report isolation, API authorization, logs, migration review and advisor checks pass.

The Harbor & Hearth demo is fictional. The controlled canonical modeled recoverable opportunity is **$392,570.56**. It is not verified savings. The HHR-07 overtime indicator is supporting evidence and must never be counted as a second financial opportunity.
