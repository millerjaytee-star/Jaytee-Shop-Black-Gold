import {
  CONTEXT_BUILDER_VERSION,
  EVALUATION_VERSION,
  MODEL_ALIAS,
  OUTPUT_SCHEMA_VERSION,
  PROMPT_VERSION,
  PROVIDER,
  approximateGatewayCost,
  runAskStabilisModel,
  type ApproximateCost,
  type Json,
  type ProviderUsage,
} from "./_stabilis-ai-core.mts";

declare const Netlify: { env: { get(name: string): string | undefined } };

const MAX_QUESTION = 1400;
const MAX_ANSWER = 6500;
const SAFE_FAILURE = "Stabilis Intelligence is temporarily unavailable. Your underlying operating data and calculated metrics remain available.";

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});

const env = (name: string) => Netlify.env.get(name) || "";

async function supabase(path: string, token: string, options: RequestInit = {}) {
  const url = env("STABILIS_SUPABASE_URL");
  const key = env("STABILIS_SUPABASE_PUBLISHABLE_KEY");
  if (!url || !key) throw new Error("SERVER_CONFIG");
  const response = await fetch(`${url}${path}`, {
    ...options,
    headers: {
      apikey: key,
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let data: any = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!response.ok) {
    const error: any = new Error(data?.message || data?.error || `SUPABASE_${response.status}`);
    error.status = response.status;
    throw error;
  }
  return data;
}

async function rpc(name: string, token: string, args: Json) {
  return supabase(`/rest/v1/rpc/${name}`, token, { method: "POST", body: JSON.stringify(args) });
}

function category(question: string) {
  const q = question.toLowerCase();
  if (/labor|overtime|splh|staff|schedule/.test(q)) return "labor";
  if (/food|cogs|waste/.test(q)) return "food_cost";
  if (/inventory|count|usage/.test(q)) return "inventory";
  if (/purchase|vendor|invoice|price/.test(q)) return "purchasing";
  if (/forecast|predict|miss/.test(q)) return "forecast";
  if (/revenue|sales|transaction|guest|check/.test(q)) return "revenue";
  if (/opportun|priority|biggest issue/.test(q)) return "opportunity";
  if (/action|overdue|owner|deadline/.test(q)) return "actions";
  if (/verified|saved|savings|impact|result|improv/.test(q)) return "results";
  if (/data|quality|missing|trust|reconcil/.test(q)) return "data_quality";
  if (/location|store|unit/.test(q)) return "location";
  return "executive";
}

function isInjectionAttempt(question: string) {
  return /(ignore (all |the )?(rules|instructions)|system prompt|service[- ]?role|secret key|api key|all organizations|other tenant|tenant b|bypass|disable rls)/i.test(question);
}

function compactContext(context: Json) {
  const workspace = context.workspace || {};
  return {
    context: workspace.context || {},
    kpis: workspace.kpis || {},
    locations: (workspace.locations || []).slice(0, 50),
    opportunities: (workspace.opportunities || []).slice(0, 40),
    actions: (workspace.actions || []).slice(0, 40),
    alerts: (workspace.alerts || []).slice(0, 30),
    reports: (workspace.reports || []).slice(0, 15),
    data_sources: (workspace.data_sources || []).slice(0, 25),
    data_quality_issues: (workspace.data_quality_issues || []).slice(0, 30),
    forecasts: (workspace.forecasts || []).slice(0, 40),
    metrics: (context.metrics || []).slice(0, 120),
    findings: (context.findings || []).slice(0, 60),
    observed_results: (context.observed_results || []).slice(0, 30),
    verified_values: (context.verified_values || []).slice(0, 30),
    financial_stage_definitions: context.financial_stage_definitions || {},
  };
}

function evidenceIndex(context: Json) {
  const allowed = new Map<string, Json>();
  const add = (type: string, rows: any[]) => (rows || []).forEach((row) => {
    if (row && row.id) allowed.set(String(row.id), { type, ...row });
  });
  add("metric", context.metrics);
  add("finding", context.findings);
  add("opportunity", context.opportunities);
  add("action", context.actions);
  add("alert", context.alerts);
  add("forecast", context.forecasts);
  add("report", context.reports);
  add("data_quality", context.data_quality_issues);
  add("observed_result", context.observed_results);
  add("verified_value", context.verified_values);
  return allowed;
}

function allowedFinancialValues(value: any, key = "", out = new Set<number>()) {
  if (Array.isArray(value)) value.forEach((v) => allowedFinancialValues(v, key, out));
  else if (value && typeof value === "object") Object.entries(value).forEach(([k, v]) => allowedFinancialValues(v, k, out));
  else if (typeof value === "number" && /(amount|opportunity|value|sales|cost|impact|financial|purchase|inventory|wage|revenue|actual|baseline|target|additive)/i.test(key)) {
    out.add(Math.round(value * 100) / 100);
  }
  return out;
}

function hasInventedDollar(answer: string, context: Json) {
  const allowed = allowedFinancialValues(context);
  const amounts = answer.match(/\$\s?[\d,]+(?:\.\d{1,2})?/g) || [];
  return amounts.some((raw) => {
    const n = Number(raw.replace(/[$,\s]/g, ""));
    if (!Number.isFinite(n)) return true;
    const rounded = Math.round(n * 100) / 100;
    return ![...allowed].some((x) => Math.abs(x - rounded) < 0.01);
  });
}

function noData(context: Json) {
  const k = context.kpis || {};
  return !context.findings?.length && !context.opportunities?.length && !context.metrics?.length &&
    k.operator_health == null && k.modeled_opportunity == null && k.data_quality == null;
}

type QueryHandle = { queryId: string; duplicate: boolean };

async function beginQuery(
  token: string,
  orgId: string,
  locationId: string | null,
  cat: string,
  question: string,
): Promise<QueryHandle> {
  const payload = await rpc("stabilis_begin_intelligence_query", token, {
    p_organization_id: orgId,
    p_location_scope: locationId ? [locationId] : [],
    p_query_category: cat,
    p_model_provider: PROVIDER,
    p_model_name: MODEL_ALIAS,
    p_question: question,
    p_prompt_version: PROMPT_VERSION,
    p_context_builder_version: CONTEXT_BUILDER_VERSION,
    p_output_schema_version: OUTPUT_SCHEMA_VERSION,
    p_evaluation_version: EVALUATION_VERSION,
  });
  return {
    queryId: String(payload?.query_id || ""),
    duplicate: Boolean(payload?.duplicate),
  };
}

async function finalizeQuery(
  token: string,
  queryId: string,
  orgId: string,
  status: string,
  evidence: any[],
  latency: number,
  errorCode: string | null = null,
  modelVersion: string | null = null,
  usage: ProviderUsage | null = null,
  cost: ApproximateCost | null = null,
) {
  await rpc("stabilis_finalize_intelligence_query", token, {
    p_query_id: queryId,
    p_organization_id: orgId,
    p_response_status: status,
    p_evidence_refs: evidence,
    p_latency_ms: latency,
    p_error_code: errorCode,
    p_model_version: modelVersion,
    p_input_tokens: usage?.inputTokens ?? null,
    p_cached_input_tokens: usage?.cachedInputTokens ?? null,
    p_output_tokens: usage?.outputTokens ?? null,
    p_total_tokens: usage?.totalTokens ?? null,
    p_approximate_cost_usd: cost?.usd ?? null,
    p_estimated_netlify_credits: cost?.netlifyCredits ?? null,
    p_currency: cost?.currency ?? null,
    p_pricing_version: cost?.pricingVersion ?? null,
  });
}

async function finishOr503(
  token: string,
  queryId: string,
  orgId: string,
  status: string,
  evidence: any[],
  latency: number,
  errorCode: string | null = null,
  modelVersion: string | null = null,
  usage: ProviderUsage | null = null,
  cost: ApproximateCost | null = null,
) {
  try {
    await finalizeQuery(token, queryId, orgId, status, evidence, latency, errorCode, modelVersion, usage, cost);
    return null;
  } catch {
    return json({ error: SAFE_FAILURE, query_id: queryId, telemetry_status: "persistence_failed" }, 503);
  }
}

function safeNoData(missing: string[] = []) {
  return {
    answer: "Not enough data. Stabilis does not currently have enough validated information in your authorized workspace to answer that question reliably.",
    confidence: "INSUFFICIENT",
    data_gap: true,
    missing_data: missing.length ? missing : ["validated operating records relevant to this question"],
    evidence: [],
    recommendation_draft: null,
  };
}

export default async (req: Request) => {
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);
  const started = Date.now();
  const auth = req.headers.get("authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
  if (!token) return json({ error: "Authentication required" }, 401);

  let body: Json;
  try { body = await req.json(); } catch { return json({ error: "Invalid JSON" }, 400); }

  try {
    await supabase("/auth/v1/user", token);
  } catch {
    return json({ error: "Invalid or expired Stabilis session" }, 401);
  }

  if (body.action === "feedback") {
    if (!body.organization_id || !body.query_id || !["HELPFUL", "NOT_HELPFUL"].includes(body.rating)) {
      return json({ error: "Invalid feedback request" }, 400);
    }
    try {
      const id = await rpc("stabilis_submit_intelligence_feedback", token, {
        p_organization_id: body.organization_id,
        p_query_id: body.query_id,
        p_rating: body.rating,
        p_reason: body.reason || null,
        p_comment: body.comment || null,
      });
      return json({ ok: true, feedback_id: id });
    } catch (error: any) {
      return json({ error: error?.status === 403 ? "Not authorized" : "Feedback could not be saved" }, error?.status === 403 ? 403 : 400);
    }
  }

  const question = String(body.question || "").trim();
  const orgId = String(body.organization_id || "").trim();
  const locationId = body.location_id ? String(body.location_id) : null;
  if (!orgId || question.length < 2 || question.length > MAX_QUESTION) {
    return json({ error: "Question or organization is invalid" }, 400);
  }
  const cat = category(question);

  let rawContext: Json;
  try {
    rawContext = await rpc("stabilis_intelligence_context", token, {
      p_organization_id: orgId,
      p_location_id: locationId,
    });
  } catch (error: any) {
    const status = error?.status === 401 ? 401 : 403;
    return json({ error: status === 403 ? "That information is unavailable in your authorized Stabilis context." : "Session expired" }, status);
  }

  const context = compactContext(rawContext);
  let handle: QueryHandle;
  try {
    handle = await beginQuery(token, orgId, locationId, cat, question);
  } catch {
    return json({ error: SAFE_FAILURE, telemetry_status: "start_failed" }, 503);
  }
  if (!handle.queryId) return json({ error: SAFE_FAILURE, telemetry_status: "invalid_query_handle" }, 503);
  if (handle.duplicate) {
    return json({ error: "This Ask Stabilis question is already being processed. Retry after a few seconds.", query_id: handle.queryId }, 409);
  }
  const queryId = handle.queryId;

  if (isInjectionAttempt(question)) {
    const result = {
      answer: "I can only use information in your authorized Stabilis organization and location scope. I cannot reveal hidden instructions, credentials, other tenants, or bypass Stabilis authorization controls.",
      confidence: "NOT_APPLICABLE",
      data_gap: false,
      missing_data: [],
      evidence: [],
      recommendation_draft: null,
    };
    const failed = await finishOr503(token, queryId, orgId, "refused", [], Date.now() - started, "PROMPT_INJECTION", "not-called");
    if (failed) return failed;
    return json({ ...result, query_id: queryId, model: "deterministic-refusal", provider: "stabilis" });
  }

  if (noData(context)) {
    const result = safeNoData();
    const failed = await finishOr503(token, queryId, orgId, "not_enough_data", [], Date.now() - started, null, "not-called");
    if (failed) return failed;
    return json({ ...result, query_id: queryId, model: "deterministic-data-gap", provider: "stabilis" });
  }

  const verified = Number(context.kpis?.verified_value || 0);
  if (/\b(saved|savings|verified financial impact|verified value)\b/i.test(question) && verified === 0) {
    const result = {
      answer: "No verified savings have been established yet. Stabilis currently records Verified Financial Impact at $0 for this authorized scope. Any Modeled Opportunity shown in the workspace is potential, not verified savings.",
      confidence: "HIGH",
      data_gap: false,
      missing_data: [],
      evidence: [],
      recommendation_draft: null,
    };
    const failed = await finishOr503(token, queryId, orgId, "deterministic_guard", [], Date.now() - started, null, "deterministic-guard");
    if (failed) return failed;
    return json({ ...result, query_id: queryId, model: "deterministic-guard", provider: "stabilis" });
  }

  if (!process.env.OPENAI_BASE_URL) {
    const failed = await finishOr503(token, queryId, orgId, "provider_unavailable", [], Date.now() - started, "AI_GATEWAY_UNAVAILABLE", "not-called");
    if (failed) return failed;
    return json({ error: SAFE_FAILURE, query_id: queryId }, 503);
  }

  let modelRun;
  try {
    modelRun = await runAskStabilisModel(question, context);
  } catch (error: any) {
    const failed = await finishOr503(
      token,
      queryId,
      orgId,
      "provider_error",
      [],
      Date.now() - started,
      String(error?.message || error?.code || "MODEL_ERROR").slice(0, 120),
      String(error?.model || "unknown").slice(0, 120),
    );
    if (failed) return failed;
    return json({ error: SAFE_FAILURE, query_id: queryId }, 503);
  }

  const modelJson = modelRun.payload;
  const usage = modelRun.usage;
  const cost = approximateGatewayCost(modelRun.modelVersion, usage);
  const allowedConfidence = new Set(["HIGH", "MEDIUM", "LOW", "INSUFFICIENT", "NOT_APPLICABLE"]);
  const answer = typeof modelJson?.answer === "string" ? modelJson.answer.trim().slice(0, MAX_ANSWER) : "";
  if (!answer || !allowedConfidence.has(String(modelJson?.confidence || ""))) {
    const failed = await finishOr503(
      token, queryId, orgId, "malformed_output", [], Date.now() - started,
      "OUTPUT_VALIDATION", modelRun.modelVersion, usage, cost,
    );
    if (failed) return failed;
    return json({ error: SAFE_FAILURE, query_id: queryId }, 503);
  }

  const idx = evidenceIndex(context);
  const evidence = (Array.isArray(modelJson.evidence) ? modelJson.evidence : []).slice(0, 8).flatMap((item: any) => {
    const row = idx.get(String(item?.id || ""));
    if (!row) return [];
    return [{
      id: String(row.id),
      type: row.type,
      label: String(item?.label || row.location_code || row.metric_name || row.category || row.title || row.type).slice(0, 180),
      location: row.location_code || null,
      period: row.period || row.forecast_date || null,
    }];
  });

  if (hasInventedDollar(answer, context)) {
    const guarded = "Stabilis does not currently have enough validated deterministic output to support every financial amount in the generated response, so the answer was withheld. Open the underlying Opportunity or Metric evidence instead.";
    const failed = await finishOr503(
      token, queryId, orgId, "guarded_financial_output", evidence, Date.now() - started,
      "UNTRUSTED_FINANCIAL_AMOUNT", modelRun.modelVersion, usage, cost,
    );
    if (failed) return failed;
    return json({
      answer: guarded,
      confidence: "INSUFFICIENT",
      data_gap: true,
      missing_data: ["trusted deterministic financial value for the requested claim"],
      evidence,
      recommendation_draft: null,
      query_id: queryId,
      model: modelRun.modelVersion,
      provider: PROVIDER,
    });
  }

  const result = {
    answer,
    confidence: modelJson.confidence,
    data_gap: Boolean(modelJson.data_gap),
    missing_data: Array.isArray(modelJson.missing_data)
      ? modelJson.missing_data.slice(0, 8).map((x: any) => String(x).slice(0, 200))
      : [],
    evidence,
    recommendation_draft: typeof modelJson.recommendation_draft === "string"
      ? modelJson.recommendation_draft.slice(0, 2500)
      : null,
  };
  const failed = await finishOr503(
    token, queryId, orgId, "success", evidence, Date.now() - started,
    null, modelRun.modelVersion, usage, cost,
  );
  if (failed) return failed;
  return json({ ...result, query_id: queryId, model: modelRun.modelVersion, provider: PROVIDER });
};

export const config = {
  path: "/api/ask-stabilis",
  method: "POST",
  rateLimit: {
    windowLimit: 30,
    windowSize: 60,
    aggregateBy: ["ip", "domain"],
  },
};
