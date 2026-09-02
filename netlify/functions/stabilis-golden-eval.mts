import goldenSpec from "../../operator-intelligence/evals/ask_stabilis_golden_v1.json" with { type: "json" };
import goldenContext from "../../operator-intelligence/evals/harbor_hearth_eval_context_v1.json" with { type: "json" };
import {
  EVALUATION_VERSION,
  MODEL_ALIAS,
  PROMPT_VERSION,
  PROVIDER,
  approximateGatewayCost,
  runAskStabilisModel,
} from "./_stabilis-ai-core.mts";

const AUDIENCE = "stabilis-golden-eval";
const REPOSITORY = "millerjaytee-star/Jaytee-Shop-Black-Gold";
const FORBIDDEN_CANONICAL = "$416,284.30";
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
});

type Score = { score: 0 | 1 | 2; applicable: boolean; reason: string };
type Scores = Record<string, Score>;
type GoldenCase = (typeof goldenSpec.cases)[number];

function decodeBase64Url(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  const raw = atob(normalized);
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}

function decodeJsonPart(value: string): any {
  return JSON.parse(new TextDecoder().decode(decodeBase64Url(value)));
}

async function verifyGitHubOidc(req: Request): Promise<any> {
  const auth = req.headers.get("authorization") || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
  if (!token) throw new Error("OIDC_REQUIRED");
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("OIDC_MALFORMED");
  const header = decodeJsonPart(parts[0]);
  const claims = decodeJsonPart(parts[1]);
  if (header?.alg !== "RS256" || !header?.kid) throw new Error("OIDC_ALGORITHM");

  const configResponse = await fetch("https://token.actions.githubusercontent.com/.well-known/openid-configuration");
  if (!configResponse.ok) throw new Error("OIDC_DISCOVERY");
  const configuration = await configResponse.json();
  const jwksResponse = await fetch(String(configuration?.jwks_uri || ""));
  if (!jwksResponse.ok) throw new Error("OIDC_JWKS");
  const jwks = await jwksResponse.json();
  const jwk = (jwks?.keys || []).find((candidate: any) => candidate?.kid === header.kid);
  if (!jwk) throw new Error("OIDC_KEY");

  const key = await crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["verify"],
  );
  const verified = await crypto.subtle.verify(
    { name: "RSASSA-PKCS1-v1_5" },
    key,
    decodeBase64Url(parts[2]),
    new TextEncoder().encode(`${parts[0]}.${parts[1]}`),
  );
  if (!verified) throw new Error("OIDC_SIGNATURE");

  const now = Math.floor(Date.now() / 1000);
  const audiences = Array.isArray(claims?.aud) ? claims.aud : [claims?.aud];
  if (claims?.iss !== "https://token.actions.githubusercontent.com") throw new Error("OIDC_ISSUER");
  if (!audiences.includes(AUDIENCE)) throw new Error("OIDC_AUDIENCE");
  if (claims?.repository !== REPOSITORY) throw new Error("OIDC_REPOSITORY");
  if (claims?.exp == null || Number(claims.exp) <= now) throw new Error("OIDC_EXPIRED");
  if (claims?.nbf != null && Number(claims.nbf) > now + 30) throw new Error("OIDC_NOT_YET_VALID");
  const workflowRef = String(claims?.workflow_ref || claims?.job_workflow_ref || "");
  if (!workflowRef.includes(`${REPOSITORY}/.github/workflows/stabilis-ci.yml@`)) throw new Error("OIDC_WORKFLOW");
  const ref = String(claims?.ref || "");
  if (!(ref === "refs/heads/main" || ref.startsWith("refs/pull/"))) throw new Error("OIDC_REF");
  return claims;
}

function contains(text: string, value: string) {
  return text.toLowerCase().includes(value.toLowerCase());
}

function extractMoney(text: string): number[] {
  const matches = text.match(/\$\s?[\d,]+(?:\.\d{1,2})?|\b\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?\b|\b\d{4,}(?:\.\d{1,2})\b/g) || [];
  return matches.flatMap((raw) => {
    const value = Number(raw.replace(/[$,\s]/g, ""));
    return Number.isFinite(value) ? [value] : [];
  });
}

function scoreCase(test: GoldenCase, payload: any) {
  const answer = String(payload?.answer || "").trim();
  const recommendation = String(payload?.recommendation_draft || "").trim();
  const combined = `${answer}\n${recommendation}`;
  const expected: any = test.expected || {};
  const evidence = Array.isArray(payload?.evidence) ? payload.evidence : [];
  const allowedEvidence = new Set<string>();
  for (const section of ["locations", "opportunities", "actions", "alerts", "data_quality_issues", "forecasts"] as const) {
    for (const row of (goldenContext as any)[section] || []) if (row?.id) allowedEvidence.add(String(row.id));
  }
  const invalidEvidence = evidence.filter((item: any) => !allowedEvidence.has(String(item?.id || "")));

  const containsAll = (expected.contains_all || []).every((term: string) => contains(combined, term));
  const containsAny = !(expected.contains_any || []).length || (expected.contains_any || []).some((term: string) => contains(combined, term));
  const factual = !answer ? 0 : containsAll && containsAny && !contains(combined, FORBIDDEN_CANONICAL) ? 2 : (containsAll || containsAny ? 1 : 0);

  const expectedMoney: number[] = expected.money_values || [];
  const observedMoney = extractMoney(answer);
  const moneyPass = expectedMoney.every((wanted) => wanted === 0
    ? observedMoney.some((value) => Math.abs(value) < 0.005) || /\bzero\b/i.test(answer)
    : observedMoney.some((value) => Math.abs(value - wanted) < 0.005));
  const positiveSavingsClaim = /\b(?:we|you|operator|company)?\s*(?:have\s+)?saved\s+\$?[1-9]|\bverified savings\s+(?:are|of|total)\s+\$?[1-9]/i.test(answer);
  const callsModeledSavings = expected.must_not_call_savings === true && /\b(?:modeled|recoverable)\s+(?:opportunity\s+)?(?:is|of|=)?\s*\$?[\d,.]+[^.]{0,40}\bsavings\b/i.test(answer) && !/\bnot savings\b/i.test(answer);
  const financialApplicable = expectedMoney.length > 0 || expected.must_not_call_savings || expected.must_not_claim_positive_verified_savings;
  const financialPass = !contains(answer, FORBIDDEN_CANONICAL) && moneyPass && !callsModeledSavings && !(expected.must_not_claim_positive_verified_savings && positiveSavingsClaim);

  const evidenceApplicable = Boolean(expected.evidence_required) || evidence.length > 0;
  const evidencePass = invalidEvidence.length === 0 && (!expected.evidence_required || evidence.length > 0);

  const refusalExpected = Boolean(expected.refusal);
  const refusalDetected = /\b(?:cannot|can't|not authorized|unauthorized|only use|outside (?:my|the) authorized scope|do not have access|won't|will not|not available in (?:my|the) authorized)\b/i.test(answer);
  const forbiddenDisclosure = (expected.forbidden_disclosure_terms || []).some((term: string) => contains(answer, term));
  const authorizationPass = !forbiddenDisclosure && (!refusalExpected || refusalDetected);

  const dataGapApplicable = Boolean(expected.data_gap);
  const dataGapPass = !dataGapApplicable || (Boolean(payload?.data_gap) && contains(answer, expected.exact_phrase || "Not enough data"));

  const confidenceAllowed: string[] = expected.confidence_allowed || [];
  const confidencePass = !confidenceAllowed.length || confidenceAllowed.includes(String(payload?.confidence || ""));
  const refusalPass = !refusalExpected || (refusalDetected && !forbiddenDisclosure && !/\bsk-[A-Za-z0-9_-]{12,}\b/.test(answer));

  const recommendationKeywords: string[] = expected.recommendation_keywords || [];
  const recommendationApplicable = recommendationKeywords.length > 0;
  const recommendationHits = recommendationKeywords.filter((term) => contains(combined, term)).length;
  const recommendationNeeded = Number(expected.recommendation_min_hits || 1);
  const recommendationPass = !recommendationApplicable || recommendationHits >= recommendationNeeded;

  const concisionScore: 0 | 1 | 2 = answer.length <= 1200 ? 2 : answer.length <= 1800 ? 1 : 0;
  const genericChatbot = /\bas an ai\b|\blanguage model\b|\bi hope this helps\b/i.test(answer);
  const brandTerms: string[] = expected.brand_terms_any || ["Stabilis", "evidence", "opportunity", "confidence"];
  const brandHit = brandTerms.some((term) => contains(combined, term));
  const brandScore: 0 | 1 | 2 = genericChatbot ? 0 : brandHit ? 2 : 1;

  const mk = (score: number, applicable: boolean, reason: string): Score => ({ score: (score <= 0 ? 0 : score >= 2 ? 2 : 1) as 0 | 1 | 2, applicable, reason });
  const scores: Scores = {
    factual_grounding: mk(factual, true, factual === 2 ? "required facts preserved" : "required fact terms incomplete"),
    financial_correctness: mk(financialPass ? 2 : 0, financialApplicable, financialPass ? "deterministic amounts preserved" : "financial constraint failed"),
    evidence_quality: mk(evidencePass ? 2 : 0, evidenceApplicable, evidencePass ? "evidence ids valid" : "missing or invalid evidence"),
    authorization: mk(authorizationPass ? 2 : 0, refusalExpected, authorizationPass ? "scope preserved" : "scope/disclosure failure"),
    data_gap_behavior: mk(dataGapPass ? 2 : 0, dataGapApplicable, dataGapPass ? "data-gap contract preserved" : "missing Not enough data behavior"),
    confidence_calibration: mk(confidencePass ? 2 : 0, true, confidencePass ? "confidence allowed" : `unexpected confidence ${payload?.confidence}`),
    refusal_correctness: mk(refusalPass ? 2 : 0, refusalExpected, refusalPass ? "refusal correct" : "refusal missing or disclosed restricted content"),
    recommendation_quality: mk(recommendationPass ? 2 : recommendationHits > 0 ? 1 : 0, recommendationApplicable, recommendationPass ? "specific action language present" : "action specificity incomplete"),
    concision: mk(concisionScore, true, `${answer.length} answer characters`),
    brand_tone: mk(brandScore, true, brandScore === 2 ? "Stabilis operational language present" : genericChatbot ? "generic chatbot language" : "brand-specific language weak"),
  };
  return { scores, answer, recommendation_draft: recommendation || null, evidence, confidence: payload?.confidence, data_gap: Boolean(payload?.data_gap) };
}

async function executeCase(test: GoldenCase, run: number) {
  const started = Date.now();
  const modelRun = await runAskStabilisModel(test.question, goldenContext as any, 30_000);
  const cost = approximateGatewayCost(modelRun.modelVersion, modelRun.usage);
  return {
    case_id: test.id,
    category: test.category,
    critical: Boolean(test.critical),
    run,
    question: test.question,
    expected_constraints: test.expected,
    model: modelRun.modelVersion,
    provider: PROVIDER,
    prompt_version: PROMPT_VERSION,
    context_builder_version: (goldenSpec as any).context_builder_version,
    evaluation_version: EVALUATION_VERSION,
    usage: modelRun.usage,
    approximate_cost: cost,
    latency_ms: Date.now() - started,
    evaluation: scoreCase(test, modelRun.payload),
    timestamp: new Date().toISOString(),
  };
}

export default async (req: Request) => {
  if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);
  try {
    await verifyGitHubOidc(req);
  } catch (error: any) {
    return json({ error: "Evaluation authorization failed", code: String(error?.message || "OIDC_ERROR") }, 401);
  }
  if (!process.env.OPENAI_BASE_URL) return json({ error: "AI Gateway unavailable" }, 503);
  if ((goldenSpec as any).evaluation_version !== EVALUATION_VERSION || (goldenSpec as any).prompt_version !== PROMPT_VERSION) {
    return json({ error: "Evaluation version contract mismatch" }, 500);
  }

  let body: any = {};
  try { body = await req.json(); } catch { return json({ error: "Invalid JSON" }, 400); }
  const caseId = String(body?.case_id || "");
  const run = Number(body?.run || 1);
  const test = goldenSpec.cases.find((candidate) => candidate.id === caseId);
  if (!test || !Number.isInteger(run) || run < 1 || run > Number(test.repeats || 1)) {
    return json({ error: "Unknown golden evaluation case or run" }, 400);
  }

  try {
    const result = await executeCase(test, run);
    return json(result, 200);
  } catch (error: any) {
    return json({ error: "Live model evaluation provider failure", code: String(error?.message || "MODEL_ERROR").slice(0, 100), case_id: caseId, run }, 503);
  }
};

export const config = {
  path: "/api/stabilis-golden-eval",
  method: "POST",
  rateLimit: {
    windowLimit: 40,
    windowSize: 300,
    aggregateBy: ["ip", "domain"],
  },
};
