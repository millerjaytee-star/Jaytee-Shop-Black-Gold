const plan = { forecast_sales: 10000, target_pct: 25, scheduled_hours: 125, scheduled_cost: 2500 };

export const exampleWeeks = [
  {
    start: '2026-11-02',
    sales: [1100, 1150, 1200, 1250, 1500, 1550, 1250],
    hours: [14, 14, 16, 19, 25, 26, 21],
    paid: [280, 280, 320, 380, 500, 520, 420]
  },
  {
    start: '2026-11-09',
    sales: [1200, 1250, 1300, 1300, 1500, 1650, 1300],
    hours: [14, 15, 16, 18, 21, 23, 18],
    paid: [280, 300, 320, 360, 420, 460, 360]
  }
];

const sum = values => values.reduce((total, value) => total + value, 0);
export const exampleInputs = exampleWeeks.map(week => ({
  ...plan,
  actual_sales: sum(week.sales),
  actual_hours: sum(week.hours),
  actual_cost: sum(week.paid)
}));

const [baseline] = exampleInputs;

export const exampleScenarios = [
  {
    id: 'schedule', name: 'Overbuilt schedule',
    inputs: { ...baseline, actual_sales: 10000, scheduled_hours: 135, scheduled_cost: 2700 }
  },
  {
    id: 'sales', name: 'Sales-only miss',
    inputs: { ...baseline, actual_hours: 125, actual_cost: 2500 }
  },
  {
    id: 'missing-forecast', name: 'Missing sales forecast',
    inputs: { ...baseline, forecast_sales: null }
  },
  {
    id: 'varying-rates', name: 'Different average pay rates',
    inputs: { ...baseline, actual_sales: 10000, actual_hours: 125, actual_cost: 2625 }
  },
  {
    id: 'zero-sales', name: 'Zero recorded sales',
    inputs: { ...baseline, actual_sales: 0 }
  }
];

// Customer reviews use the database calculation. This version serves fictional examples.
export function calculateExample(input) {
  const has = (...keys) => keys.every(key => Number.isFinite(input[key]));
  const target = input.target_pct / 100;
  const laborRate = has('actual_cost', 'actual_sales') && input.actual_sales > 0
    ? input.actual_cost / input.actual_sales * 100 : null;
  const round = value => value === null ? null : Math.sign(value) * Math.round(Math.abs(value) * 100) / 100;
  const metrics = {
    actual_pct: laborRate,
    points_over: laborRate !== null && has('target_pct') ? laborRate - input.target_pct : null,
    hours_over: has('actual_hours', 'scheduled_hours') ? input.actual_hours - input.scheduled_hours : null,
    schedule_effect: has('scheduled_cost', 'forecast_sales', 'target_pct') ? input.scheduled_cost - input.forecast_sales * target : null,
    sales_effect: has('forecast_sales', 'actual_sales', 'target_pct') ? (input.forecast_sales - input.actual_sales) * target : null,
    payroll_effect: has('actual_cost', 'scheduled_cost') ? input.actual_cost - input.scheduled_cost : null,
    total_over: has('actual_cost', 'actual_sales', 'target_pct') ? input.actual_cost - input.actual_sales * target : null
  };
  return Object.fromEntries(Object.entries(metrics).map(([key, value]) => [key, round(value)]));
}
