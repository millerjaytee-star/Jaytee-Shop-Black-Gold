import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import {calculateExample, exampleInputs, exampleScenarios, exampleWeeks} from '../assets/labor-example.js';
import {parseWeeklyCSV} from '../assets/labor-review.js';

const bridge = ({schedule_effect, sales_effect, payroll_effect, total_over}) =>
  [schedule_effect, sales_effect, payroll_effect, total_over];

test('both fictional café weeks match the aggregate CSVs and the displayed variance', () => {
  const files = ['../assets/labor-review-example.csv', '../assets/labor-examples/following-week.csv'];
  for (const [index, path] of files.entries()) {
    const parsed = parseWeeklyCSV(readFileSync(new URL(path, import.meta.url), 'utf8'));
    assert.equal(parsed.week_start, exampleWeeks[index].start);
    for (const [key, value] of Object.entries(exampleInputs[index])) assert.equal(Number(parsed[key]), value);
  }
  const [baseline, following] = exampleInputs.map(calculateExample);
  assert.deepEqual(baseline, {
    actual_pct: 30, points_over: 5, hours_over: 10,
    schedule_effect: 0, sales_effect: 250, payroll_effect: 200, total_over: 450
  });
  assert.deepEqual(bridge(following), [0, 125, 0, 125]);
  assert.equal(baseline.total_over - following.total_over, 325);
});

test('scenario bridge separates schedule, forecast, pay and unavailable percentages', () => {
  const cases = Object.fromEntries(exampleScenarios.map(({id, inputs}) => [id, calculateExample(inputs)]));
  assert.deepEqual(bridge(cases.schedule), [200, 0, 0, 200]);
  assert.deepEqual(bridge(cases.sales), [0, 250, 0, 250]);
  assert.deepEqual(bridge(cases['missing-forecast']), [null, null, 200, 450]);
  assert.equal(cases['missing-forecast'].hours_over, 10);
  assert.deepEqual(bridge(cases['varying-rates']), [0, 0, 125, 125]);
  assert.equal(cases['varying-rates'].hours_over, 0);
  assert.deepEqual(bridge(cases['zero-sales']), [0, 2500, 200, 2700]);
  assert.equal(cases['zero-sales'].actual_pct, null);
  assert.equal(cases['zero-sales'].points_over, null);
});
