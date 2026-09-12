import test from 'node:test';
import assert from 'node:assert/strict';
import scout from '../netlify/functions/stabilis-opportunity-scout.mts';

const request = () => new Request('https://example.test/api/stabilis-opportunity-scout', {headers: {authorization: 'Bearer test-only'}});
function setup(t) {
  const previous = globalThis.Netlify;
  globalThis.Netlify = {env: {get: name => name === 'STABILIS_OPPORTUNITY_SCOUT_TOKEN' ? 'test-only' : ''}};
  t.after(() => { globalThis.Netlify = previous; });
}

test('unauthorized requests never spend provider credits', async t => {
  setup(t);
  const fetch = t.mock.method(globalThis, 'fetch', () => { throw Error('must not fetch'); });
  assert.equal((await scout(new Request('https://example.test/api/stabilis-opportunity-scout'))).status, 404);
  assert.equal(fetch.mock.callCount(), 0);
});

test('runs at most two searches concurrently and retains partial evidence', async t => {
  setup(t);
  let active = 0, peak = 0, calls = 0;
  t.mock.method(globalThis, 'fetch', async () => {
    const call = ++calls;
    peak = Math.max(peak, ++active);
    await new Promise(resolve => setTimeout(resolve, 15));
    active--;
    if (call === 2) throw Error('upstream timeout');
    return Response.json({success: true, data: {web: [{url: 'https://example.org/news', title: 'New locations in Maryland 2026'}]}});
  });
  const result = await (await scout(request())).json();
  assert.equal(calls, 3);
  assert.equal(peak, 2);
  assert.equal(result.leadCount, 1);
  assert.equal(result.partial, true);
  assert.equal(result.leads[0].signals.includes('recent_signal'), false);
  assert.equal(result.leads[0].publishedAt, null);
  assert.equal(result.persistence.status, 'not_enabled');
});

test('awards recency only for dated evidence in the past 30 days', async t => {
  setup(t);
  t.mock.method(globalThis, 'fetch', async () => Response.json({data: {web: [
    {url: 'https://example.org/current', title: 'Maryland expansion', date: new Date(Date.now() - 86400000).toISOString()},
    {url: 'https://example.org/old', title: 'Latest Maryland expansion 2026', date: '2020-01-01'},
    {url: 'https://example.org/future', title: 'Maryland expansion', date: '2099-01-01'},
  ]}}));
  const result = await (await scout(request())).json();
  assert.deepEqual(result.leads.filter(x => x.signals.includes('recent_signal')).map(x => x.url), ['https://example.org/current']);
});
