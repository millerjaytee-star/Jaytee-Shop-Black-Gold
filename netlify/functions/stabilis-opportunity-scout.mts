declare const Netlify: { env: { get(name: string): string | undefined } };

type SourceType = "web" | "news";

type FirecrawlRow = {
  url?: string;
  title?: string;
  description?: string;
  snippet?: string;
  date?: string;
  position?: number;
};

type Lead = {
  url: string;
  title: string;
  description: string;
  sourceType: SourceType;
  score: number;
  status: "CONTACT_NOW" | "RESEARCH_FURTHER" | "WATCH" | "IGNORE";
  signals: string[];
  publishedAt: string | null;
};

const FIRECRAWL_SEARCH_URL = "https://api.firecrawl.dev/v2/search";

const QUERIES = [
  "Washington DC Maryland Northern Virginia DMV multi-unit restaurant retail expansion new locations coming soon opening 2026",
  "Washington DC Maryland Northern Virginia restaurant retail district manager regional manager director of operations hiring multi-unit 2026",
  "Washington DC Maryland Northern Virginia multi-unit restaurant retail operational problems service delays inventory labor leadership complaints 2026",
] as const;

const J = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });

function text(row: FirecrawlRow): string {
  return `${row.title || ""} ${row.description || row.snippet || ""}`.toLowerCase();
}

function scoreRow(row: FirecrawlRow, now = Date.now()): { score: number; signals: string[] } {
  const haystack = text(row);
  let score = 0;
  const signals: string[] = [];

  if (/coming soon|new location|opening|expand|expansion|franchis|second location|third location/.test(haystack)) {
    score += 25;
    signals.push("expansion");
  }
  if (/multi-unit|locations|regional|restaurant group|portfolio|chain|franchise/.test(haystack)) {
    score += 15;
    signals.push("multi_unit");
  }
  if (/district manager|regional manager|director of operations|vp of operations|operations manager/.test(haystack)) {
    score += 20;
    signals.push("operations_leadership_hiring");
  }
  if (/washington,? d\.?c\.?|washington dc|maryland|northern virginia|arlington|alexandria|fairfax|bethesda|silver spring|dmv/.test(haystack)) {
    score += 15;
    signals.push("dmv_presence");
  }
  if (/complaint|delay|slow service|inventory|labor shortage|turnover|understaff|closure|violation|service issue|operational/.test(haystack)) {
    score += 15;
    signals.push("operating_friction");
  }
  // Recency requires a parseable source date, not marketing words or a year.
  const published = Date.parse(row.date || "");
  if (Number.isFinite(published) && published <= now && now - published <= 30 * 86_400_000) {
    score += 10;
    signals.push("recent_signal");
  }

  return { score: Math.min(score, 100), signals };
}

function statusFor(score: number): Lead["status"] {
  if (score >= 80) return "CONTACT_NOW";
  if (score >= 60) return "RESEARCH_FURTHER";
  if (score >= 40) return "WATCH";
  return "IGNORE";
}

async function search(query: string, apiKey: string): Promise<{ rows: Array<{ row: FirecrawlRow; sourceType: SourceType }>; credits: number }> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (apiKey) headers.authorization = `Bearer ${apiKey}`;

  // Search-first, scrape-later: do not attach scrapeOptions here. This keeps
  // broad lead discovery cheap and avoids unexpectedly scraping long PDFs/pages.
  const response = await fetch(FIRECRAWL_SEARCH_URL, {
    method: "POST",
    headers,
    body: JSON.stringify({
      query,
      limit: 8,
      tbs: "qdr:m",
      sources: [{ type: "web" }, { type: "news" }],
    }),
    signal: AbortSignal.timeout(20_000),
  });

  const payload: any = await response.json();
  if (!response.ok || payload?.success === false) {
    throw new Error(String(payload?.error || payload?.message || `HTTP ${response.status}`).slice(0, 240));
  }

  const rows: Array<{ row: FirecrawlRow; sourceType: SourceType }> = [];
  for (const sourceType of ["web", "news"] as const) {
    const group = Array.isArray(payload?.data?.[sourceType]) ? payload.data[sourceType] : [];
    for (const row of group) rows.push({ row, sourceType });
  }

  return {
    rows,
    credits: Number(payload?.creditsUsed ?? payload?.data?.creditsUsed ?? 0) || 0,
  };
}

export default async (req: Request) => {
  if (req.method !== "GET") return J({ ok: false }, 405);

  const url = new URL(req.url);
  const challenge = Netlify.env.get("STABILIS_OPPORTUNITY_SCOUT_TOKEN") || "";
  const suppliedToken = req.headers.get("authorization")?.replace(/^Bearer /i, "") || url.searchParams.get("token");
  if (!challenge || suppliedToken !== challenge) return J({ ok: false }, 404);

  const apiKey = Netlify.env.get("FIRECRAWL_API_KEY") || "";
  const errors: string[] = [];
  const candidates: Lead[] = [];
  let creditsUsed = 0;

  const startedAt = Date.now();
  // Two at a time: avoid serial latency without exceeding a small account limit.
  for (let offset = 0; offset < QUERIES.length; offset += 2) {
    const batch = await Promise.allSettled(QUERIES.slice(offset, offset + 2).map(query => search(query, apiKey)));
    for (const outcome of batch) {
      try {
        if (outcome.status === "rejected") throw outcome.reason;
        const result = outcome.value;
        creditsUsed += result.credits;
        for (const { row, sourceType } of result.rows) {
          const url = String(row.url || "").trim();
          if (!url) continue;
          const { score, signals } = scoreRow(row);
          candidates.push({
            url,
            title: String(row.title || url),
            description: String(row.description || row.snippet || "").slice(0, 700),
            sourceType,
            score,
            status: statusFor(score),
            signals,
            publishedAt: Number.isFinite(Date.parse(row.date || "")) ? new Date(row.date!).toISOString() : null,
          });
        }
      } catch (error: any) {
        errors.push(String(error?.message || "Firecrawl search failed").slice(0, 240));
      }
  }
  }

  const bestByUrl = new Map<string, Lead>();
  for (const lead of candidates) {
    const current = bestByUrl.get(lead.url);
    if (!current || lead.score > current.score) bestByUrl.set(lead.url, lead);
  }

  const leads = [...bestByUrl.values()]
    .sort((a, b) => b.score - a.score)
    .slice(0, 25);

  return J({
    ok: leads.length > 0,
    mode: apiKey ? "authenticated" : "keyless",
    fetchedAt: new Date().toISOString(),
    creditsUsed,
    durationMs: Date.now() - startedAt,
    partial: errors.length > 0 && leads.length > 0,
    persistence: { status: "not_enabled" },
    leadCount: leads.length,
    leads,
    errors,
    note: "Discovery signals require human/analyst verification before outreach. No CRM write or outbound message is triggered by this endpoint.",
  });
};

export const config = {
  path: "/api/stabilis-opportunity-scout",
  method: "GET",
  rateLimit: {
    windowLimit: 5,
    windowSize: 60,
    aggregateBy: ["ip", "domain"],
  },
};
