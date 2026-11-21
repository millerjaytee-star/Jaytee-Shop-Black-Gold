import assert from 'node:assert/strict';
import { test } from 'node:test';
import { prepareDiagnosticReadout, renderDiagnosticReadout } from '../assets/diagnostic-readout.js';

const context = { organizationId: 'org', locationId: 'cafe', locationName: 'Fictional café', startDate: '2026-10-26' };
const inScope = { organization_id: context.organizationId, location_id: context.locationId };
const makeWeek = fields => ({
  ...inScope, id: 'weekly-review', status: 'compared', week_start: '2026-10-26', source: 'Approved schedule and payroll <exports>',
  inputs: { actual_sales: 9000, target_pct: 25, scheduled_hours: 125, actual_hours: 135, actual_cost: 2700 },
  metrics: { total_over: 450, actual_pct: 30, hours_over: 10, schedule_effect: 0, sales_effect: 250, payroll_effect: 200 },
  followup: { comparable: true, observed_change: 325, week_start: '2026-11-02', source: 'Following-week payroll' }, ...fields
});
const note = { ...inScope, id: 'inventory-note', note_date: '2026-10-29', context_type: 'INVENTORY', body: 'Diagnostic inventory evidence\nClosing count missing.' };
const action = { title: 'Compare closing coverage', assignee_name: 'Fictional GM', assignee_id: 'gm', approved_by: 'owner',
  due_date: '2026-11-01', next_review: '2026-11-08', target_measure: '125 paid hours', evidence_required: 'Closing timecards' };

test('includes released source records and the matching inventory note only', () => {
  const reviews = [makeWeek(), makeWeek({ id: 'draft', status: 'draft' }), makeWeek({ id: 'wrong-location', location_id: 'other' }), makeWeek({ id: 'wrong-org', organization_id: 'other' })];
  const notes = [note, { ...note, id: 'wrong-note', location_id: 'other' }, { ...note, id: 'general-note', body: 'Delivery shortage' }];
  const data = prepareDiagnosticReadout({ ...context, reviews, notes });
  assert.deepEqual(data.weeks.map(item => item.id), ['weekly-review']);
  assert.deepEqual(data.inventory.map(item => item.id), ['inventory-note']);
  const html = renderDiagnosticReadout(data, context);
  assert.match(html, /#labor-review\/cafe\/weekly-review/);
  assert.match(html, /\$450/);
  assert.match(html, /\$325/);
  assert.match(html, /No approved estimate in this review/);
  assert.match(html, /No finance validation recorded/);
  assert.match(html, /Approved schedule and payroll &lt;exports&gt;/);
  assert.match(html, /Closing count missing/);
  assert.doesNotMatch(html, /wrong-location|wrong-org|wrong-note|Delivery shortage/);
});

test('takes at most five actually approved actions and assigns phases from their due dates', () => {
  const weeks = Array.from({ length: 8 }, (_, index) => makeWeek({
    id: 'week-' + index, week_start: '2026-10-' + String(index + 11), action: { ...action }
  }));
  weeks[0].action.approved_by = '';
  weeks[1].action.assignee_id = '';
  weeks[7].action.due_date = '2026-12-10';
  const plan = prepareDiagnosticReadout({ ...context, reviews: weeks, notes: [] });
  assert.equal(plan.actions.length, 5);
  assert.equal(plan.remainingActions, 1);
  assert.ok(plan.actions.every(item => item.phase === 0));
  const phased = prepareDiagnosticReadout({ ...context, reviews: [{ ...weeks[7], action: { ...action, due_date: '2026-12-10' } }], notes: [] });
  assert.equal(phased.actions[0].phase, 1);
  const html = renderDiagnosticReadout(phased, context);
  assert.match(html, /Days 31–60[\s\S]*Compare closing coverage/);
  assert.match(html, /Fictional GM/);
  assert.match(html, /Closing timecards/);
});

test('distinguishes no observed improvement, incomparable weeks and documented finance results', () => {
  const rows = [
    makeWeek({ id: 'no-improvement', followup: { comparable: true, observed_change: 0 } }),
    makeWeek({ id: 'incomparable', followup: { comparable: false, observed_change: 777 } }),
    makeWeek({ id: 'verified', status: 'verified', verification: { amount: 100 } })
  ];
  const html = renderDiagnosticReadout(prepareDiagnosticReadout({ ...context, reviews: rows, notes: [] }), context);
  assert.match(html, /Observed change<\/dt><dd>\$0/);
  assert.match(html, /Observed change<\/dt><dd>Weeks marked incomparable/);
  assert.match(html, /Client-verified financial impact<\/dt><dd>\$100/);
  assert.doesNotMatch(html, /\$777/);
});
