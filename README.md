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

**REAL FINANCIAL DATA RELEASE GATE = BLOCKED** pending positive-path login/session/password-reset/invitation testing in the deployed application. Do not upload real restaurant financial data until that gate is explicitly changed to PASSED.

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
