import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

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
    assert.doesNotMatch(html, /calendly\.com|\$500\s+(?:profit leak )?diagnostic|\b(?:15|30)[- ]minute\s+(?:operations conversation|(?:margin recovery |profit leak score )?review)/i, name);
    if (name !== "index.html") {
      assert.match(html, /href="\/#diagnostic">Request a 20-minute fit call<\/a>/, name);
    }
  }
});

test("pilot scope survives a website copy edit", () => {
  for (const name of ["index.html", "resources.html", "profit-control-reset.html"]) {
    const html = read(name);
    assert.match(html, /14-Day Margin Recovery Diagnostic/i, name);
    assert.match(html, /\$1,500/, name);
    assert.match(html, /one[- ]location/i, name);
  }
  const home = read("index.html");
  assert.match(home, /<form\b[^>]*data-netlify="true"/i);
  assert.match(home, /<option\b[^>]*>[^<]*3[–-]15[^<]*<\/option>/i);
  assert.doesNotMatch(home, /\$499/i);
  assert.match(read("profit-control-reset.html"), /agreed separately/i);
  assert.doesNotMatch(read("thanks.html"), /calendly\.com|15[- ]minute|\$500\b/i);
});
