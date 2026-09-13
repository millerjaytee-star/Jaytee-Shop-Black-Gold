import test from 'node:test';
import assert from 'node:assert/strict';
import { analyze, observe, parseCSV, scenario, toCSV } from '../assets/control-room/engine.mjs';

const complete = { location: 'Test location', sales: 10000, labor: 3500, hours: 500, overtime: 20, laborTarget: 30, minimumHours: 450, cogs: 3400, cogsTarget: 30, overhead: 1200, openingInventory: 1000, purchases: 3000, transfersIn: 0, transfersOut: 0, closingInventory: 900 };

test('analyze separates modeled labor and COGS gaps from other findings', () => {
  const result = analyze(complete, 7);
  assert.equal(result.metrics.profit, 1900);
  assert.equal(result.modeledGap, 900);
  assert.ok(result.issues.some((issue) => issue.id === 'labor'));
  assert.ok(result.issues.some((issue) => issue.id === 'cogs'));
});

test('scenario respects the minimum service-hours floor', () => {
  assert.throws(() => scenario(complete, { salesChange: 0, hoursChange: -20, cogsPointChange: 0, investment: 0 }, 7), /minimum service hours/);
  const result = scenario(complete, { salesChange: 5, hoursChange: 0, cogsPointChange: -1, investment: 100 }, 7);
  assert.equal(result.sales, 10500);
  assert.equal(result.change, 335);
});

test('observation requires comparable period data and evidence', () => {
  const action = { category: 'labor', days: 7, baselineSales: 10000, baselineCost: 3500 };
  assert.throws(() => observe(action, { sales: 10000, cost: 3200, investment: 0, days: 7, evidence: '' }), /source evidence/);
  assert.equal(observe(action, { sales: 10000, cost: 3200, investment: 50, days: 7, evidence: 'Payroll export' }).observedNet, 250);
});

test('CSV parsing validates rows and exported strings cannot execute spreadsheet formulas', () => {
  const rows = parseCSV('location,sales,labor,hours\nA,1000,300,50');
  assert.equal(rows[0].location, 'A');
  assert.match(toCSV([{ ...complete, location: '=SUM(A1:A2)' }]), /"'=SUM\(A1:A2\)"/);
  assert.throws(() => parseCSV('location,sales\nA,nope'), /nonnegative number/);
});
