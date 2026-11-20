import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const diagnosticDays = 14;
const fitCallMinutes = 20;
const fitCall = `${fitCallMinutes}-minute fit call`;
const fee = '$1,500';
const locationRange = '3–15';
const territory = 'Washington, DC, Maryland or Northern Virginia';
const name = `${diagnosticDays}-Day Margin Recovery Diagnostic`;

const copy = {
  name,
  fee,
  range: locationRange,
  call: fitCall,
  cta: `Request a ${fitCall}`,
  summary: `${diagnosticDays}-day diagnostic · ${fee} for one location`,
  description: `The ${name} is a ${fee} fixed-fee founding pilot for one agreed location.`,
  audience: `For restaurant, café and bakery groups with ${locationRange} locations in ${territory}.`,
  start: `The ${diagnosticDays} calendar days start on the agreed date after signed scope, cleared payment in full and minimum data readiness.`,
};

export const foundingOfferSlots = {
  'index.html': ['cta', 'cta', 'summary', 'audience', 'name', 'fee', 'start', 'call', 'range', 'cta'],
  'resources.html': ['description', 'audience', 'cta'],
  'profit-control-reset.html': ['description', 'cta'],
  'new-store-operational-readiness.html': ['cta'],
  'off-premise-line-accuracy.html': ['cta'],
  'labor-kds-workflow.html': ['cta'],
  'proof-ledger.html': ['cta'],
  'operator-intelligence-report.html': ['cta'],
  'thanks.html': ['call'],
};

export function renderFoundingOffer(html) {
  const marker = /(<([a-z][a-z0-9-]*)\b[^>]*\bdata-offer="([a-z]+)"[^>]*>)[^<]*(<\/\2>)/g;
  const slots = [];
  const rendered = html.replace(marker, (_, opening, _tag, slot, closing) => {
    if (!Object.hasOwn(copy, slot)) throw new Error(`Unknown founding offer field: ${slot}`);
    slots.push(slot);
    const escaped = copy[slot].replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
    return opening + escaped + closing;
  });
  return { rendered, slots };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const check = process.argv.includes('--check');
  for (const [page, expected] of Object.entries(foundingOfferSlots)) {
    const path = new URL('../' + page, import.meta.url);
    const html = readFileSync(path, 'utf8');
    const { rendered, slots } = renderFoundingOffer(html);
    if (slots.join() !== expected.join()) throw new Error(`Check the founding offer fields in ${page}.`);
    if (html !== rendered) {
      if (check) throw new Error(`Founding offer copy in ${page} is out of date.`);
      writeFileSync(path, rendered);
    }
  }
}
