const released = new Set(['released', 'assigned', 'accepted', 'change_requested', 'evidence_submitted', 'compared', 'verified']);
const inventoryPrefix = 'Diagnostic inventory evidence\n';
const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2, minimumFractionDigits: 0 });
const quantity = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
const fields = {
  forecast_sales: 'sales forecast', actual_sales: 'actual net sales', target_pct: 'labor target',
  scheduled_hours: 'scheduled hours', actual_hours: 'paid hours', scheduled_cost: 'scheduled labor dollars', actual_cost: 'paid labor dollars'
};
const actionStates = {
  assigned: 'Awaiting GM acceptance', accepted: 'In progress', change_requested: 'Change requested',
  evidence_submitted: 'Evidence submitted', compared: 'Evidence reviewed', verified: 'Finance validated'
};
const phases = [
  ['Days 1–30', 'Reconcile the baseline and check the first action in a comparable week.'],
  ['Days 31–60', 'Check remaining gaps and review the trend against the same measure.'],
  ['Days 61–90', 'Decide which controls to keep and record any eligible client finance validation.']
];

const escape = value => String(value ?? '').replace(/[&<>"']/g, key => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[key]);
const money = figure => Number.isFinite(figure) ? currency.format(figure) : 'Needs data';
const number = (figure, suffix) => Number.isFinite(figure) ? quantity.format(figure) + suffix : 'Needs data';
const isoDay = value => /^\d{4}-\d{2}-\d{2}$/.test(value || '') ? Date.parse(value + 'T00:00:00Z') / 86400000 : NaN;

export function prepareDiagnosticReadout({ reviews, notes, organizationId, locationId, startDate = '' }) {
  const inScope = row => row.organization_id === organizationId && row.location_id === locationId;
  const weeks = reviews.filter(row => inScope(row) && released.has(row.status) && Number.isFinite(isoDay(row.week_start)))
    .sort((first, second) => second.week_start.localeCompare(first.week_start)).slice(0, 8);
  const inventory = notes.filter(row => inScope(row) && row.context_type === 'INVENTORY' && row.body?.startsWith(inventoryPrefix))
    .map(row => ({ id: row.id, date: row.note_date, body: row.body.slice(inventoryPrefix.length) }));
  const actions = weeks.filter(row => row.action?.approved_by && row.action?.assignee_id)
    .sort((first, second) => (first.action.due_date || '9999').localeCompare(second.action.due_date || '9999'))
    .map(row => {
      const dueOffset = isoDay(row.action.due_date) - isoDay(startDate);
      const phase = Number.isFinite(dueOffset) && dueOffset < 90 ? Math.floor(Math.max(0, dueOffset) / 30) : null;
      return { ...row.action, status: row.status, reviewId: row.id, phase, dueBeforePlan: dueOffset < 0 };
    });
  return { weeks, inventory, actions: actions.slice(0, 5), remainingActions: Math.max(0, actions.length - 5) };
}

function evidenceFields(record) {
  const comparable = record.followup?.comparable;
  const observed = comparable ? money(record.followup?.observed_change) : record.followup ? 'Weeks marked incomparable' : 'Comparison pending';
  const verification = record.status === 'verified' && Number.isFinite(record.verification?.amount) ?
    money(record.verification.amount) : 'No finance validation recorded';
  return [['Modeled opportunity', 'No approved estimate in this review'], ['Observed change', observed], ['Client-verified financial impact', verification]];
}

function facts(items) {
  return '<dl class="diagnostic-facts">' + items.map(([label, value]) => `<div><dt>${escape(label)}</dt><dd>${escape(value)}</dd></div>`).join('') + '</dl>';
}

function reviewLink(locationId, reviewId, label) {
  return `<a href="#labor-review/${encodeURIComponent(locationId)}/${encodeURIComponent(reviewId)}">${escape(label)}</a>`;
}

function weekCard(record, locationId) {
  const metrics = record.metrics || {};
  const missing = Object.entries(fields).filter(([key]) => !Number.isFinite(record.inputs?.[key])).map(([, label]) => label);
  const release = (record.history || []).filter(event => event.operation === 'release').at(-1);
  return `<li>
    <h3>${reviewLink(locationId, record.id, 'Week of ' + record.week_start)}</h3>
    <p><strong>Baseline source.</strong> ${escape(record.source || 'Source reference unavailable.')}</p>
    ${release?.note ? `<p><strong>Analyst release.</strong> ${escape(release.note)}</p>` : ''}
    ${facts([
      ['Historical variance at actual sales', money(metrics.total_over)],
      ['Actual labor', record.inputs?.actual_sales === 0 ? 'Unavailable at zero net sales' : number(metrics.actual_pct, '%')],
      ['Hours above or below schedule', number(metrics.hours_over, ' h')],
      ['Schedule effect', money(metrics.schedule_effect)], ['Sales effect', money(metrics.sales_effect)], ['Payroll effect', money(metrics.payroll_effect)],
      ...evidenceFields(record)
    ])}
    ${missing.length ? `<p><strong>Data gaps.</strong> ${escape(missing.join(', '))}.</p>` : ''}
    ${record.followup ? `<p><strong>Comparison source.</strong> Week of ${escape(record.followup.week_start)}. ${escape(record.followup.source || 'Source reference unavailable.')}</p>` : ''}
  </li>`;
}

function roadmapAction(action, locationId) {
  return `<li><h4>${reviewLink(locationId, action.reviewId, action.title)}</h4>
    ${facts([['Owner', action.assignee_name], ['Due', (action.due_date || 'Date needed') + (action.dueBeforePlan ? ' · Before roadmap start' : '')], ['Target measure', action.target_measure || 'Recorded measure needed'],
      ['Evidence', action.evidence_required || 'Evidence instructions needed'], ['Next review', action.next_review], ['Status', actionStates[action.status] || 'Approved']])}</li>`;
}

function list(items, render, empty) {
  return items.length ? '<ul class="diagnostic-items">' + items.map(render).join('') + '</ul>' : `<p>${escape(empty)}</p>`;
}

export function renderDiagnosticReadout(data, context) {
  const { weeks, inventory, actions, remainingActions } = data;
  const { locationId, locationName, startDate, laborUnavailable } = context;
  return `<p><strong>Location.</strong> ${escape(locationName)}</p>
    <section class="card"><div class="card-head"><h2>Released labor findings</h2></div><div class="card-body">
      <p>${weeks.length} released ${weeks.length === 1 ? 'week is' : 'weeks are'} included. The diagnostic calls for eight complete weeks of daily net sales, scheduled labor and actual paid labor by role. Supporting coverage is in the linked review records.</p>
      ${laborUnavailable ? '<p role="status">Weekly labor evidence is unavailable. Reopen the readout when the workspace is available.</p>' :
        list(weeks, record => weekCard(record, locationId), 'Released weekly findings will appear after analyst review.')}
    </div></section>
    <section class="card"><div class="card-head"><h2>Inventory and waste evidence</h2></div><div class="card-body">
      ${list(inventory, note => `<li><h3>Shared note · ${escape(note.date)}</h3><p class="diagnostic-note">${escape(note.body)}</p><small>Source note ${escape(note.id)}</small></li>`, 'No shared diagnostic evidence is recorded. Check the matched closed four-week inventory period, opening and closing counts, purchases, available waste records and the latest location P&L.')}
    </div></section>
    <section class="card"><div class="card-head"><h2>90-day roadmap</h2></div><div class="card-body">
      <p>${startDate ? 'Plan starts ' + escape(startDate) + '.' : 'Enter the agreed roadmap start date to place approved actions by due date.'} The roadmap shows up to five approved actions in due-date order. ${remainingActions ? `${remainingActions} later ${remainingActions === 1 ? 'action remains' : 'actions remain'} in the weekly workspace.` : ''}</p>
      ${phases.map(([title, description], index) => `<section class="diagnostic-stage"><h3>${title}</h3><p>${description}</p>${list(actions.filter(action => action.phase === index), action => roadmapAction(action, locationId), 'No approved action is due in this phase.')}</section>`).join('')}
      ${actions.some(action => action.phase === null) ? `<section class="diagnostic-stage"><h3>${startDate ? 'Outside the selected 90 days or date needed' : 'Approved actions awaiting a roadmap date'}</h3>${list(actions.filter(action => action.phase === null), action => roadmapAction(action, locationId), '')}</section>` : ''}
    </div></section>`;
}

export async function openDiagnosticReadout(host, context) {
  const { rpc, organizationId, locationId, notes } = context;
  host.innerHTML = '<p role="status">Loading released findings and evidence…</p>';
  let reviews = [];
  let laborUnavailable = false;
  try {
    reviews = await rpc('stabilis_labor_reviews', { p_organization_id: organizationId, p_location_id: locationId });
  } catch {
    laborUnavailable = true;
  }
  if (!host.isConnected) return;
  host.innerHTML = `<div class="diagnostic-toolbar">
    <label for="roadmap-start">Roadmap start date</label>
    <input class="control" id="roadmap-start" type="date">
    <button class="btn primary" type="button" data-diagnostic-print>Print diagnostic readout</button>
    <p>The date applies to this view and its export. Keep client copies in the restricted folder named in the signed scope.</p>
  </div><div class="diagnostic-readout-content"></div>`;
  const start = host.querySelector('#roadmap-start');
  const content = host.querySelector('.diagnostic-readout-content');
  const render = () => {
    const view = { ...context, startDate: start.value, laborUnavailable };
    content.innerHTML = renderDiagnosticReadout(prepareDiagnosticReadout({ ...view, reviews: reviews || [], notes }), view);
  };
  start.addEventListener('change', render);
  host.querySelector('[data-diagnostic-print]').addEventListener('click', () => window.print());
  render();
}
