# Stabilis Firecrawl Opportunity Scout

## Purpose

The Opportunity Scout adds a protected, server-side Firecrawl discovery layer to Stabilis. It looks for public DMV operating signals that can identify high-value consulting prospects without changing the existing Operator Intelligence financial engine or customer data model.

The scout currently searches for three signal groups:

1. expansion / openings / coming-soon activity;
2. District, Regional, or Operations leadership hiring;
3. public operating-friction signals such as service, labor, inventory, or execution problems.

## Scoring

Each discovered URL is scored from public search evidence:

- expansion: +25
- multi-unit signal: +15
- operations-leadership hiring: +20
- DMV presence: +15
- operating friction: +15
- recent signal: +10

Statuses:

- 80–100: `CONTACT_NOW`
- 60–79: `RESEARCH_FURTHER`
- 40–59: `WATCH`
- under 40: `IGNORE`

The score is a prospecting priority score, not a claim that the source is accurate. High-value leads still require verification before outreach.

## Endpoint

`GET /api/stabilis-opportunity-scout?token=<secret>`

Required server-side Netlify secret:

`STABILIS_OPPORTUNITY_SCOUT_TOKEN`

Optional Firecrawl account key:

`FIRECRAWL_API_KEY`

When the Firecrawl key is absent, the code can use Firecrawl starter keyless search where available. The secret token remains mandatory either way so this endpoint cannot be used as a public credit-spending proxy.

## Credit discipline

The scout uses a **search-first, scrape-later** policy. Discovery requests do not automatically scrape or summarize every matched page. This protects the credit budget, particularly when a result points to a large PDF or long page.

Only a later analyst/collector step should scrape a selected high-value URL when deeper evidence is needed.

## Safety boundary

The endpoint:

- does not write to the Stabilis customer database;
- does not alter Operator Intelligence financial calculations;
- does not send email or outbound sales messages;
- does not auto-contact prospects;
- does not expose the Firecrawl API key;
- does not treat scraped/search text as verified financial truth.

The existing external Firecrawl recurring monitor can continue serving as the scheduled discovery mechanism. This endpoint gives the Stabilis codebase an on-demand internal scout using the same signal model.
