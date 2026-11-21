import assert from 'node:assert/strict';
import { test } from 'node:test';
import { explainWeeklyLaborReview, isWeeklyLaborQuestion } from '../netlify/lib/weekly-labor-answer.mts';

const locationId = '11111111-1111-1111-1111-111111111111';
const baseline = {
  id: 'baseline', week_start: '2026-10-26', status: 'released',
  metrics: { actual_pct: 30, hours_over: 10, schedule_effect: 0, sales_effect: 250, payroll_effect: 200, total_over: 450 }
};
const question = 'What drove the variance in my weekly labor review?';

test('explains released deterministic values and cites the selected location and original period', () => {
  assert.equal(isWeeklyLaborQuestion(question), true);
  assert.equal(isWeeklyLaborQuestion('What was labor on 2026-10-26?'), true);
  assert.equal(isWeeklyLaborQuestion('What is the largest modeled opportunity?'), false);
  const response = explainWeeklyLaborReview(question, [{ ...baseline, id: 'draft', status: 'draft' }, baseline], locationId);
  assert.match(response.answer, /\$450 above target/);
  assert.match(response.answer, /30% of net sales/);
  assert.match(response.answer, /10 above schedule/);
  assert.match(response.answer, /Schedule against its forecast budget was \$0/);
  assert.match(response.answer, /Sales effect was \$250/);
  assert.match(response.answer, /Paid labor against schedule was \$200/);
  assert.match(response.answer, /Modeled opportunity\. No approved estimate/);
  assert.match(response.answer, /Client-verified financial impact\. No finance validation/);
  assert.deepEqual(response.evidence, [{ id: baseline.id, type: 'weekly_labor_review', label: 'Released labor review', location_id: locationId, period: baseline.week_start }]);
});

test('withholds drafts and comparisons from a different requested week', () => {
  assert.equal(explainWeeklyLaborReview(question, [{ ...baseline, status: 'draft' }], locationId), null);
  assert.equal(explainWeeklyLaborReview(`${question} 2026-11-02`, [baseline], locationId), null);
});

test('reports missing forecast, measured hours and incomparable results separately', () => {
  const response = explainWeeklyLaborReview(question, [{
    ...baseline, metrics: { ...baseline.metrics, sales_effect: null, schedule_effect: null },
    followup: { comparable: false, observed_change: 325 }
  }], locationId);
  assert.equal(response.data_gap, true);
  assert.ok(response.missing_data.some(reason => reason.includes('forecast sales')));
  assert.match(response.answer, /10 above schedule/);
  assert.match(response.answer, /marked incomparable/);
  assert.doesNotMatch(response.answer, /\$325/);
});

test('preserves zero observed change and distinguishes it from finance validation', () => {
  const response = explainWeeklyLaborReview(question, [{
    ...baseline, status: 'compared', followup: { comparable: true, observed_change: 0 }
  }], locationId);
  assert.match(response.answer, /Observed change\. \$0\./);
  assert.match(response.answer, /Client-verified financial impact\. No finance validation/);
});
