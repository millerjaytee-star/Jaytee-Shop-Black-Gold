import {calculateExample, exampleInputs, exampleWeeks} from './labor-example.js';

(() => {
  const nav = document.getElementById('siteNav');
  const menu = document.querySelector('.menu-toggle');

  function setMenu(open) {
    menu.setAttribute('aria-expanded', String(open));
    menu.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    nav.toggleAttribute('data-open', open);
  }

  menu.addEventListener('click', () => setMenu(menu.getAttribute('aria-expanded') === 'false'));
  nav.addEventListener('click', event => {
    if (event.target.closest('a')) setMenu(false);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && nav.hasAttribute('data-open')) {
      setMenu(false);
      menu.focus();
    }
  });
  nav.setAttribute('data-menu-ready', '');

  const maxChartPercent = 40;
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const dollars = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  const controls = [...document.querySelectorAll('[data-week]')];
  const bars = [...document.querySelectorAll('#chartBars .bar')];

  function showWeek(index) {
    const week = exampleWeeks[index];
    const inputs = exampleInputs[index];
    const metrics = calculateExample(inputs);
    const weeklyRate = metrics.actual_pct.toFixed(1);
    const dailyPercentages = week.paid.map((paid, day) => 100 * paid / week.sales[day]);
    controls.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
    bars.forEach((bar, day) => {
      const percent = dailyPercentages[day];
      bar.style.setProperty('--height', (100 * percent / maxChartPercent).toFixed(2) + '%');
      bar.classList.toggle('above', percent > inputs.target_pct);
      bar.title = days[day] + ': ' + percent.toFixed(1) + '%';
    });
    document.getElementById('laborGap').textContent = dollars.format(metrics.total_over);
    document.getElementById('laborPct').textContent = weeklyRate + '%';
    document.getElementById('scheduleEffect').textContent = dollars.format(metrics.schedule_effect);
    document.getElementById('salesEffect').textContent = dollars.format(metrics.sales_effect);
    document.getElementById('payrollEffect').textContent = dollars.format(metrics.payroll_effect);
    document.getElementById('chartDescription').textContent = `Week ${index + 1} daily labor percentages. ${dailyPercentages.map((value, day) => `${days[day]} ${value.toFixed(1)}%`).join(', ')}. Weekly labor is ${weeklyRate}% of sales against a ${inputs.target_pct}% target.`;
    document.getElementById('weekSummary').textContent = `Week ${index + 1}. Labor is ${weeklyRate}% of sales and ${dollars.format(metrics.total_over)} over target. Schedule above budget ${dollars.format(metrics.schedule_effect)}, sales effect ${dollars.format(metrics.sales_effect)}, and payroll above schedule ${dollars.format(metrics.payroll_effect)}.`;
  }

  controls.forEach((button, index) => button.addEventListener('click', () => showWeek(index)));
})();
