const escaped = value => String(value ?? '').replace(/[&<>"']/g, character =>
  ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'})[character]);
const types = {sales:'Sales', schedule:'Schedule', payroll:'Paid labor'};
const measurements = {
  actual_sales:'Net sales', forecast_sales:'Forecast net sales',
  scheduled_hours:'Scheduled hours', scheduled_cost:'Scheduled labor',
  actual_hours:'Paid hours', actual_cost:'Paid labor',
  date:'Business date', location:'Location', role:'Role', daypart:'Daypart'
};
const formatDate = new Intl.DateTimeFormat('en-US', {dateStyle:'medium', timeZone:'UTC'});
const formatNumber = new Intl.NumberFormat('en-US', {maximumFractionDigits:4});
const formatMoney = new Intl.NumberFormat('en-US', {style:'currency',currency:'USD'});

export function showImportChoices(holder, {canArchive, importPlan}) {
  const files = importPlan.reports;
  const names = Array.from(new Set(files.map(file => file.filename)));
  const archive = canArchive && files.every(file => file.archiveEligible)
    ? `<label class="lr-field lr-source-consent">
        <input type="checkbox" data-archive-sources> Archive the deidentified originals privately
      </label>
      <p class="lr-help">Confirm each original contains only this location, including all workbook sheets, and that the signed scope permits storage.</p>
      <label class="lr-field">Signed retention end date<input type="date" data-retain-through disabled></label>`
    : canArchive ? '<p class="lr-help">Archive each location separately. A file with additional locations or unreviewed worksheets can contribute mapped figures only.</p>' : '';
  holder.innerHTML = `<p class="lr-help">Confirmed source mappings will be saved for ${names.map(escaped).join(', ')}.</p>${archive}
    <button type="button" data-discard-sources>Clear mapped source links</button>`;
}

export async function weeklySourcePayload({form, importPlan, payload, adapter}) {
  if (importPlan.week !== payload.week_start) {
    throw Error('The import covers a different fiscal week. Map the correct week or clear the mapped source links.');
  }
  if (Object.entries(importPlan.totals).some(([key,value]) => payload.inputs[key] !== value)) {
    throw Error('A saved input differs from its confirmed mapping. Remap the report or clear the mapped source links.');
  }
  const retaining = form.querySelector('[data-archive-sources]')?.checked;
  const retainThrough = form.querySelector('[data-retain-through]')?.value;
  if (retaining && (!retainThrough || !adapter.archiveSource)) {
    throw Error('Enter the retention end date from the signed scope.');
  }
  const archivedFiles = new Map();
  const imports = [];
  for (const {file, archiveEligible, ...report} of importPlan.reports) {
    if (retaining) {
      if (!archiveEligible || !report.sha256) throw Error('These originals cannot be archived for the selected location.');
      if (!archivedFiles.has(report.sha256)) {
        archivedFiles.set(report.sha256, await adapter.archiveSource(file, report, payload.week_start, retainThrough));
      }
      report.archive_id = archivedFiles.get(report.sha256);
    }
    imports.push(report);
  }
  return imports;
}

function groupSummary(groups) {
  if (!groups?.length) return '';
  return `<ul>${groups.map(({role,daypart,...values}) => {
    const amounts = Object.entries(values).filter(([,value]) => typeof value === 'number');
    const label = [role,daypart].filter(Boolean).map(escaped).join(' · ');
    const numbers = amounts.map(([key,value]) => escaped(measurements[key])+' '+(key.endsWith('_hours')?formatNumber.format(value)+' h':formatMoney.format(value))).join(' · ');
    return `<li>${label}${numbers?' · '+numbers:' · weekly group figures unavailable'}</li>`;
  }).join('')}</ul>`;
}
function reportSummary(report) {
  const archive = report.archive;
  const retention = archive?.retain_through ? formatDate.format(new Date(archive.retain_through+'T12:00:00Z')) : '';
  const download = archive?.path
    ? `<button type="button" data-download-source="${escaped(archive.path)}" data-source-filename="${escaped(report.filename)}" data-source-sha256="${escaped(report.sha256)}">Download private original</button> <span class="lr-help">Retained through ${retention}</span>`
    : archive ? '<p class="lr-help">The retained original is unavailable.</p>' : '<p class="lr-help">Mapping saved without a raw archive.</p>';
  const fields = Object.entries(report.mapping).map(([key,name]) => escaped(measurements[key] ?? key)+' ← '+escaped(name));
  const gaps = report.gaps.length ? '<p class="lr-help">'+report.gaps.map(escaped).join(' · ')+'</p>' : '';
  const checksum = report.sha256 ? ' · SHA-256 '+escaped(report.sha256.slice(0,16))+'…' : '';
  return `<div class="lr-source-entry"><strong>${escaped(types[report.type])} · ${escaped(report.filename)}</strong>
    <p>${escaped(report.source_location)} · ${report.coverage}/7 days · ${report.row_count} rows · ${escaped(report.sheet)} row ${report.header_row}${checksum}</p>
    <p>${fields.join(' · ')}</p>${gaps}${groupSummary(report.groups)}${download}</div>`;
}

export function showSourceHistory(holder, records) {
  holder.innerHTML = records.map(record => {
    const week = record.week_start ? formatDate.format(new Date(record.week_start+'T12:00:00Z')) : '';
    const notes = record.reports.length ? record.reports.map(reportSummary).join('') : '<p class="lr-help">Manual source references.</p>';
    return `<div><h3>Version ${record.version}${week?' · '+week:''}</h3><p class="lr-help">${escaped(record.source)}</p>${notes}</div>`;
  }).join('') || '<p>No saved source mappings are available.</p>';
}

export async function archiveWeeklySource({rpc, storage, scope, file, report, week, retainThrough}) {
  const entry = await rpc('stabilis_prepare_weekly_source', {
    ...scope, p_week_start:week, p_filename:report.filename, p_sha256:report.sha256,
    p_size_bytes:file.size, p_retain_through:retainThrough
  });
  const finish = () => rpc('stabilis_finish_weekly_source', {...scope,p_source_id:entry.id});
  if (!entry.archived) {
    try {
      await storage(entry.path, {method:'POST',body:file});
    } catch (error) {
      try { await finish(); return entry.id; }
      catch { throw error; }
    }
  }
  await finish();
  return entry.id;
}

export async function checkArchivedFile(file, expectedChecksum) {
  const bytes = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  const checksum = Array.from(new Uint8Array(bytes), byte => byte.toString(16).padStart(2,'0')).join('');
  if (checksum !== expectedChecksum) throw Error('The archived file differs from its confirmed checksum. Contact the pilot administrator.');
}
