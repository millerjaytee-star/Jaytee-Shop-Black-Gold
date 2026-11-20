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

  // Fictional, aggregate café records. Both weeks have the same forecast, target and schedule.
  const weeks = [
    { sales: [1100, 1150, 1200, 1250, 1500, 1550, 1250], hours: [14, 14, 16, 19, 25, 26, 21] },
    { sales: [1200, 1250, 1300, 1300, 1500, 1650, 1300], hours: [14, 15, 16, 18, 21, 23, 18] }
  ];
  const forecastSales = 10000;
  const scheduledHours = 125;
  const hourlyRate = 20;
  const target = 0.25;
  const maxChartPercent = 40;
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
  const dollars = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  const sum = values => values.reduce((total, value) => total + value, 0);
  const controls = [...document.querySelectorAll('[data-week]')];
  const bars = [...document.querySelectorAll('#chartBars .bar')];

  function showWeek(index) {
    const week = weeks[index];
    const actualSales = sum(week.sales);
    const scheduledPay = scheduledHours * hourlyRate;
    const actualPay = sum(week.hours) * hourlyRate;
    const weeklyRate = (100 * actualPay / actualSales).toFixed(1);
    const salesEffect = target * (forecastSales - actualSales);
    const payrollEffect = actualPay - scheduledPay;
    const gap = actualPay - target * actualSales;
    const dailyPercentages = week.hours.map((hours, day) => 100 * hours * hourlyRate / week.sales[day]);
    controls.forEach((button, i) => button.setAttribute('aria-pressed', String(i === index)));
    bars.forEach((bar, day) => {
      const percent = dailyPercentages[day];
      bar.style.setProperty('--height', (100 * percent / maxChartPercent).toFixed(2) + '%');
      bar.classList.toggle('above', percent > target * 100);
      bar.title = days[day] + ': ' + percent.toFixed(1) + '%';
    });
    document.getElementById('laborGap').textContent = dollars.format(gap);
    document.getElementById('laborPct').textContent = weeklyRate + '%';
    document.getElementById('salesEffect').textContent = dollars.format(salesEffect);
    document.getElementById('payrollEffect').textContent = dollars.format(payrollEffect);
    document.getElementById('chartDescription').textContent = 'Week ' + (index + 1) + ' daily labor percentages, Monday through Sunday: ' + dailyPercentages.map(value => value.toFixed(1)).join(', ') + '. Target: 25%.';
    document.getElementById('weekSummary').textContent = 'Week ' + (index + 1) + '. Labor is ' + weeklyRate + '% of sales and ' + dollars.format(gap) + ' over target. Sales account for ' + dollars.format(salesEffect) + ' and extra payroll for ' + dollars.format(payrollEffect) + '.';
  }

  controls.forEach((button, index) => button.addEventListener('click', () => showWeek(index)));
})();
