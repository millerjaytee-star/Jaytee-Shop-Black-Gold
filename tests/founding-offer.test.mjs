import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { foundingOfferSlots, renderFoundingOffer } from "../scripts/sync-founding-offer.mjs";

const fitCall = "Request a 20-minute fit call";
const offerPages = [
  "index.html", "resources.html", "profit-control-reset.html",
  "new-store-operational-readiness.html", "off-premise-line-accuracy.html",
  "labor-kds-workflow.html", "proof-ledger.html", "operator-intelligence-report.html",
];
const read = (name) => readFileSync(new URL("../" + name, import.meta.url), "utf8");

test("current pilot pages use one fit-call request path and retire superseded offers", () => {
  for (const name of offerPages) {
    const html = read(name);
    assert.ok(html.includes(fitCall), name + " is missing the current call wording");
    assert.doesNotMatch(html, /calendly\.com|\$(?:499|500)\b|\b(?:15|30)[- ]minute\b/i, name);
    if (name !== "index.html") {
      assert.match(html, /href="\/#diagnostic" data-offer="cta">Request a 20-minute fit call<\/a>/, name);
    }
  }
});

test("pilot scope survives a website copy edit", () => {
  for (const name of ["index.html", "resources.html", "profit-control-reset.html"]) {
    const html = read(name);
    assert.match(html, /14-Day Margin Recovery Diagnostic/i, name);
    assert.match(html, /\$1,500/, name);
    assert.match(html, /one[- ](?:agreed )?location/i, name);
  }
  const home = read("index.html");
  assert.match(home, /<form\b[^>]*name="stabilis-pilot"[^>]*method="POST"[^>]*data-netlify="true"[^>]*action="\/thanks.html"/);
  assert.match(home, /<option data-offer="range">3–15<\/option>/);
  assert.match(home, /after signed scope, cleared payment in full and minimum data readiness/);
  assert.match(read("profit-control-reset.html"), /agreed separately/i);
  assert.match(read("thanks.html"), /Fit-call request received[\s\S]*Jaytee Miller/);
  assert.doesNotMatch(read("thanks.html"), /calendly\.com|15[- ]minute|\$500\b/i);
});

test("static offer copy matches the canonical terms without JavaScript", () => {
  for (const [name, expected] of Object.entries(foundingOfferSlots)) {
    const html = read(name);
    const { rendered, slots } = renderFoundingOffer(html);
    assert.deepEqual(slots, expected, name);
    assert.equal(rendered, html, name + " needs node scripts/sync-founding-offer.mjs");
  }
});
