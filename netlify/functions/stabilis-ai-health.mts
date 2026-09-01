declare const Netlify: { env: { get(name: string): string | undefined } };

const J = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json", "cache-control": "no-store" },
});

const env = (name: string) => Netlify.env.get(name) || "";

export default async (req: Request) => {
  const url = new URL(req.url);
  const challenge = env("STABILIS_AI_HEALTH_TOKEN");
  if (!challenge || url.searchParams.get("token") !== challenge) return J({ ok: false }, 404);

  // Prefer Netlify's collision-proof AI Gateway variables. Keep the OpenAI
  // compatibility aliases as a fallback because Netlify also injects them on
  // credit-based plans unless the project supplies its own provider settings.
  const base = env("NETLIFY_AI_GATEWAY_BASE_URL") || env("OPENAI_BASE_URL");
  const key = env("NETLIFY_AI_GATEWAY_KEY") || env("OPENAI_API_KEY");
  if (!base || !key) return J({ ok: false, status: "gateway_unavailable" }, 503);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${base}/v1/chat/completions`, {
      method: "POST",
      signal: controller.signal,
      headers: { authorization: `Bearer ${key}`, "content-type": "application/json" },
      body: JSON.stringify({
        model: "gpt-5",
        response_format: { type: "json_object" },
        messages: [
          { role: "system", content: 'Return only JSON {"ok":true}.' },
          { role: "user", content: "Stabilis provider readiness check. No customer data is included." },
        ],
      }),
    });
    if (!response.ok) return J({ ok: false, status: `model_${response.status}` }, 503);
    const payload = await response.json();
    const text = payload?.choices?.[0]?.message?.content;
    let data: any = {};
    try { data = JSON.parse(text || "{}"); } catch { data = {}; }
    return J(
      { ok: data?.ok === true, provider: "netlify-ai-gateway/openai", model: "gpt-5" },
      data?.ok === true ? 200 : 503,
    );
  } catch {
    return J({ ok: false, status: "provider_error" }, 503);
  } finally {
    clearTimeout(timer);
  }
};

export const config = {
  path: "/api/stabilis-ai-health",
  method: "GET",
  rateLimit: {
    windowLimit: 5,
    windowSize: 60,
    aggregateBy: ["ip", "domain"],
  },
};
