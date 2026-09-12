# Portfolio live-data audit — September 12, 2026

This audit records direct checks, not earlier completion claims. Public pages returned HTTP 200 through live Firecrawl fetches. This is not a full authenticated browser audit or production latency benchmark.

## Verified deployment mapping

| Product | Repository/target | Observed state |
| --- | --- | --- |
| Stabilis | millerjaytee-star/Jaytee-Shop-Black-Gold; stabilis-ops-group.netlify.app | Deploy b0ea80014bcde59b38f3bd2235fe9790556ea04d. Proof page uses labeled fictional examples. |
| MarketIQ | millerjaytee-star/Jaytee-Shop-BlackGold; marketiq-sports.netlify.app | Deploy 2f3650e6da7b928a0930eb3e90899b58ec675fde. Market Clock shows a labeled demonstration. |
| Concrete | app.concretemotivation.com; Netlify project concrete-nation-staging | Current manual deployment does not provide a commit ref. Pressure-to-Purpose is a static preview. Do not assume a similarly named repository matches this deployed source. |
| AEGIS | aegis-market-intelligence-review.netlify.app | Separate review surface; real Neon database reachable. Review is not a verified continuously updating application. |

## Collection and persistence

- Firecrawl account has two active monitors: STABILIS DMV Opportunity Scout at 07:00 America/New_York, and AEGIS Daily Evidence Collector at 18:30 America/New_York.
- Stabilis monitor had not run when inspected. AEGIS had one completed manual check: five results, two matches, no errors, seven actual credits.
- Both monitors have no webhook and no configured notification destination. A separate polling importer is possible but was not verified.
- Both monitors estimate 360 credits/month each. Existing remaining balance was not available through these calls. Do not increase schedules or purchase credits without checking the account.
- Stabilis production scout has three Firecrawl queries and deliberately does not persist results. Its token and Firecrawl key presence could not be verified from the unauthorized public endpoint; the 404 is intentional protection, not proof of a broken route.
- MarketIQ production information scout explicitly returns persistence.status=not_enabled. No scheduled function was listed in either Stabilis or MarketIQ's inspected deploy.
- MarketIQ /api/live-games returned a valid ESPN response with zero NFL events for the requested default date. This verifies a response, not full provider coverage.
- MarketIQ /api/odds returned 503 with THE_ODDS_API_KEY is not configured. Do not claim live bookmaker prices work.
- Neon project AEGIS Market Intelligence (winter-salad-02426812) returned: private.data_snapshots=0, private.scan_runs=1, private.scan_results=4, public.signals=0. These are counts at inspection, not permanent values.

## Database blocker

Stabilis Operator Intelligence (vpunfmwklwjefvchvmpn) and MarketIQ Sports (oyayyprkdhmdgqqvplpb) are INACTIVE in Supabase. The two visible Concrete projects are ACTIVE_HEALTHY. The organization is on the free plan.

A Stabilis restore request was rejected by Supabase because the account has reached its two-active-free-project limit. No project was paused, deleted, upgraded, or migrated. This was a provider quota refusal, not an approval-review rejection.

The Stabilis frontend configuration directly references the inactive Stabilis database. Resume alone is unavailable under the current quota. Do not sacrifice either active Concrete database without verifying usage and explicit authorization.

## Implemented fixes in this change

- Stabilis: at most two concurrent search requests rather than three sequential ones; successful evidence retained on partial failures; duration and partial-result metadata.
- Stabilis: recency score uses source dates within 30 days, not words such as new or latest. Unknown publication time is null.
- Stabilis: support Authorization Bearer for internal calls while preserving query-token compatibility.
- Tests verify concurrency, partial failure, no unauthenticated provider calls, and date scoring. These use mocks and do not prove authenticated production collection.

Related MarketIQ change adds bounded provider timeouts, short shared-cache directives for successful odds only, freshness metadata, date input validation, header-based scout authentication, and detection timestamps after response receipt. Its 19 tests pass locally; deployment is tracked separately.

## Highest-value next implementation steps

1. Stabilis: resolve persistence capacity without disrupting Concrete. Evaluate existing Netlify Blobs for bounded public prospect snapshots if its quota is suitable; keep relational client diagnostics in the existing protected design. Import monitor results idempotently with source/detection times, then make the prospect-to-diagnostic workflow persistent. Do not scrape anew on every page view.
2. Concrete: identify the actual source of the current manual deployment. Complete the existing six-pillar seven-day plan and private check-ins first; connect reset-call and membership attribution to trusted payment events. Trend scraping is supporting research, not the blocker to an actionable member experience.
3. MarketIQ: configure an already-owned permitted odds-provider credential through the server-side secret manager. Resolve history storage, then collect forward-only observations and information events. Serve latest stored data quickly; preserve gaps and sampling uncertainty. Never substitute fictional odds.
4. AEGIS: connect the existing collector/Data Bot to private.data_snapshots with validated, symbol-linked provenance and idempotency. Verify a real write/read cycle, then make scanner evidence and forward outcomes visible. Keep the Risk Firewall and no-live-trades boundary.
5. All: choose one ingestion owner per source/profile; avoid both a monitor and an independent scheduler repeating the same search. Separate user-facing reads from scraping. Add last successful ingestion, stored record count, freshness, failure reason, and budget status to protected health views.

## Performance acceptance

Measure API p50/p95, provider wait time, cold starts, payload sizes, cache hit rate, and credits per useful record. Compare identical workloads before and after. These patches improve bounded execution; no production speed multiplier is claimed. Concurrency does not reduce credits per run. A 15-second odds cache is unsuitable for claiming tick-by-tick trading observations; historical collection must use its own provider-observed timestamps.

## Safe continuation for the other Codex session

Fetch and inspect these PRs before duplicating changes. Preserve your local uncommitted work. Verify target mappings from deployment metadata: the Stabilis and MarketIQ repos have legacy shop names. Continue the existing portfolio mandate with the blockers above. Never mark a live page as a working data pipeline without verified collection, durable write, authenticated read, and repeat ingestion without duplicates.
