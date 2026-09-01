import OpenAI from "openai";

declare const Netlify: { env: { get(name: string): string | undefined } };

const J = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { "content-type": "application/json", "cache-control": "no-store" },
});

export default async (req: Request) => {
  const url = new URL(req.url);
  const challenge = Netlify.env.get("STABILIS_AI_HEALTH_TOKEN") || "";
  if (!challenge || url.searchParams.get("token") !== challenge) return J({ ok: false }, 404);

  // Netlify AI Gateway injects OPENAI_API_KEY and OPENAI_BASE_URL into the
  // function runtime. The official OpenAI SDK consumes both automatically.
  // Do not pass customer data through this readiness check.
  if (!process.env.OPENAI_BASE_URL) return J({ ok: false, status: "gateway_unavailable" }, 503);

  const client = new OpenAI();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const completion = await client.chat.completions.create({
      model: "gpt-5",
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: 'Return only JSON {"ok":true}.' },
        { role: "user", content: "Stabilis provider readiness check. No customer data is included." },
      ],
    }, { signal: controller.signal });
    const text = completion.choices?.[0]?.message?.content;
    let data: any = {};
    try { data = JSON.parse(text || "{}"); } catch { data = {}; }
    return J(
      {
        ok: data?.ok === true,
        provider: "netlify-ai-gateway/openai",
        model: completion.model || "gpt-5",
      },
      data?.ok === true ? 200 : 503,
    );
  } catch (error: any) {
    const status = String(error?.status || error?.code || "provider_error").slice(0, 80);
    return J({ ok: false, status }, 503);
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
