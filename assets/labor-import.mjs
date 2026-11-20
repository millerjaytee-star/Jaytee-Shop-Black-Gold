import { reportTypes, fieldNames, fieldsFor, guessMapping, parseDelimited, aggregateReport, weekDates } from "./labor-import-data.mjs";

const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" })[char]);
function options(items, picked) {
  return items.map(([value, label]) => `<option value="${esc(value)}"${String(value) === String(picked) ? " selected" : ""}>${esc(label)}</option>`).join("");
}
function short(value, length) {
  const cleaned = String(value).replace(/[\r\n;]+/g, " ").trim();
  return cleaned.length > length ? cleaned.slice(0, length - 1) + "…" : cleaned;
}
async function workbook(file) {
  if (file.size > 5 * 1024 * 1024) throw Error("Choose an export under 5 MiB.");
  if (/\.xlsx$/i.test(file.name)) {
    const { readXlsx } = await import("./labor-import-xlsx.mjs");
    return readXlsx(file);
  }
  if (!/\.(csv|tsv)$/i.test(file.name)) throw Error("Choose a CSV, TSV or XLSX export.");
  const rows = parseDelimited(await file.text());
  return { names: ["Delimited report"], rows: async () => rows };
}

export function openLaborImport(form, { location = "", locationCode = "" } = {}) {
  const types = Object.keys(reportTypes);
  const state = {};
  const versions = {};
  let preview = null;
  const dialog = document.createElement("dialog");
  dialog.className = "labor-import-dialog";
  dialog.setAttribute("aria-labelledby", "labor-import-title");
  if (!document.querySelector('link[data-labor-import-style]')) {
    const css = document.createElement("link");
    css.rel = "stylesheet"; css.href = "/assets/labor-import.css"; css.dataset.laborImportStyle = "";
    document.head.append(css);
  }
  const set = (selector, value) => { dialog.querySelector(selector).textContent = value; };
  dialog.innerHTML = `
    <header><h2 id="labor-import-title">Import daily operating reports</h2>
      <button type="button" data-close aria-label="Close import">Close</button></header>
    <p>Choose deidentified daily totals for one location. Use one sales row per date and one labor row per date or role. Files are read on this device. Confirmed weekly figures and source references enter your review when you save it.</p>
    <details><summary>Download fictional examples</summary>
      <p>Juniper Café · week starting October 26, 2026. Use a 25% labor target.</p>
      <p><a download href="/assets/labor-examples/sales.csv">Sales CSV</a> · <a download href="/assets/labor-examples/schedule.csv">Schedule CSV</a> · <a download href="/assets/labor-examples/payroll.csv">Payroll CSV</a> · <a download href="/assets/labor-examples/weekly-reports.xlsx">Excel workbook (three sheets)</a></p><p>For Excel, choose the same workbook for each report and select Sales, Schedule or Payroll.</p>
    </details>
    <div class="li-fields">
      <label>Review location<input data-location required maxlength="100" value="${esc(location)}" ${location ? "readonly" : ""}></label>
      <label>Fiscal week starting<input data-week type="date" required value="${esc(form.elements.week_start.value)}" ${form.elements.week_start.readOnly ? "readonly" : ""}></label>
    </div>
    <p>Seven daily records establish a complete week. Include a zero for known closed days. Missing amounts stay empty.</p>
    ${types.map(type => `<section data-report="${type}"><h3>${esc(reportTypes[type].name)}</h3>
      <label>Report file<input type="file" accept=".csv,.tsv,.xlsx" data-file></label>
      <button class="li-clear" type="button" data-remove hidden>Remove this report</button>
      <p data-file-status aria-live="polite"></p><div data-mapping></div></section>`).join("")}
    <div class="li-footer"><button type="button" data-preview class="li-primary">Preview weekly figures</button></div>
    <p data-feedback role="status" aria-live="polite"></p><div data-result></div>`;
  document.body.append(dialog);
  const close = () => dialog.close();
  dialog.querySelector("[data-close]").addEventListener("click", close);
  dialog.addEventListener("close", () => dialog.remove(), {once:true});

  function invalidate() {
    preview = null;
    dialog.querySelector("[data-result]").replaceChildren();
    set("[data-feedback]", "");
  }
  function section(type) { return dialog.querySelector(`[data-report="${type}"]`); }
  function matchingLocation(value) {
    const selected = String(value ?? "").trim().toLowerCase();
    const destination = dialog.querySelector("[data-location]").value.trim().toLowerCase();
    return Boolean(selected && (selected === destination || selected === locationCode.trim().toLowerCase()));
  }
  function confirmAlias(part) {
    const selected = part.querySelector("[data-location-value]")?.value;
    const confirmation = part.querySelector("[data-alias]");
    if (!confirmation) return;
    confirmation.closest("label").hidden = !selected || matchingLocation(selected);
    confirmation.checked = false;
  }
  function drawLocation(type) {
    const s = state[type], part = section(type);
    if (!s?.rows) return;
    const locationCol = Number(part.querySelector('[data-field="location"]').value);
    const group = part.querySelector("[data-source-location]");
    if (locationCol === -1) {
      group.innerHTML = '<label class="li-check"><input data-single type="checkbox"> I confirm every row in this file is for the review location.</label>';
      return;
    }
    const unique = Array.from(new Set(s.rows.slice(s.headerIndex + 1).map(row => String(row[locationCol] ?? "").trim()).filter(Boolean))).sort();
    const matches = unique.filter(matchingLocation);
    group.innerHTML = `<label>Source location for this review<select data-location-value>${options([["","Choose source location"], ...unique.map(x => [x,x])], matches.length === 1 ? matches[0] : "")}</select></label>
      <label class="li-check" hidden><input data-alias type="checkbox"> I checked that this source location name or code identifies the review location.</label>`;
    confirmAlias(part);
  }
  function drawFields(type) {
    const s = state[type], part = section(type);
    const headers = s.rows[s.headerIndex];
    const fields = part.querySelector("[data-columns]");
    if (!headers?.length) throw Error("This sheet has no header or data rows.");
    const columns = headers.flatMap((v, i) => String(v ?? "").trim() ? [[i, String(v)]] : []);
    const guesses = guessMapping(type, headers);
    fields.innerHTML = fieldsFor(type).map(key =>
      `<label>${esc(fieldNames[key])}<select data-field="${key}">${options([[-1, key === "date" ? "Choose date column" : "Unmapped"], ...columns],guesses[key])}</select></label>`
    ).join("");
    drawLocation(type);
  }
  async function drawSheet(type, serial) {
    const s = state[type], part = section(type);
    const sheet = part.querySelector("[data-sheet]").value;
    const rows = await s.book.rows(sheet);
    if (serial !== versions[type] || part.querySelector("[data-sheet]")?.value !== sheet) return;
    if (rows.length < 2) throw Error("This sheet has fewer than two rows. Choose a header and at least one data row.");
    s.sheet = sheet; s.rows = rows; s.headerIndex = 0;
    const header = part.querySelector("[data-header]");
    header.innerHTML = options(rows.slice(0, 25).map((row, index) => [index, `${index + 1}. ${row.slice(0, 4).map(v => short(v ?? "",22)).join(" · ")}`]), 0);
    drawFields(type);
  }
  function failFile(type, error) {
    const part = section(type);
    if (state[type]) state[type].rows = null;
    const columns = part.querySelector("[data-columns]");
    if (columns) columns.replaceChildren();
    const locations = part.querySelector("[data-source-location]");
    if (locations) locations.replaceChildren();
    part.querySelector("[data-file-status]").textContent = error.message;
  }
  async function loadFile(type, file) {
    const part = section(type), serial = versions[type] = (versions[type] || 0) + 1;
    delete state[type];
    part.querySelector("[data-mapping]").replaceChildren();
    part.querySelector("[data-remove]").hidden = !file;
    part.querySelector("[data-file-status]").textContent = file ? "Reading report…" : "";
    if (!file) return;
    try {
      const book = await workbook(file);
      if (serial !== versions[type]) return;
      const bytes = await file.arrayBuffer();
      const digest = globalThis.crypto?.subtle ? new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)) : null;
      if (serial !== versions[type]) return;
      const ref = digest ? [...digest.slice(0,8)].map(v => v.toString(16).padStart(2,"0")).join("") : "";
      state[type] = {file,book,ref};
      part.querySelector("[data-mapping]").innerHTML = `<div class="li-fields">
        <label>Worksheet<select data-sheet>${options(book.names.map(n => [n,n]),book.names[0])}</select></label>
        <label>Header row<select data-header></select></label></div>
        <div data-columns class="li-fields"></div><div data-source-location></div>`;
      await drawSheet(type, serial);
      if (serial === versions[type]) part.querySelector("[data-file-status]").textContent = "Review the worksheet, headers and location before previewing the week.";
    } catch (error) { if (serial === versions[type]) failFile(type,error); }
  }
  dialog.addEventListener("change", async event => {
    invalidate();
    const target = event.target;
    const type = target.closest("[data-report]")?.dataset.report;
    if (!type) return;
    try {
      if (target.matches("[data-file]")) await loadFile(type,target.files[0]);
      else if (target.matches("[data-sheet]")) {
        const serial = ++versions[type];
        state[type].rows = null;
        await drawSheet(type, serial);
        if (state[type].rows) section(type).querySelector("[data-file-status]").textContent = "Review the worksheet, headers and location.";
      }
      else if (target.matches("[data-header]")) { state[type].headerIndex = Number(target.value); drawFields(type); }
      else if (target.matches('[data-field="location"]')) drawLocation(type);
      else if (target.matches("[data-location-value]")) confirmAlias(section(type));
    } catch (error) { failFile(type,error); }
  });
  dialog.addEventListener("input", event => {
    if (event.target.matches("[data-location],[data-week]")) invalidate();
    if (event.target.matches("[data-location]")) for (const type of types) confirmAlias(section(type));
  });

  function prepare() {
    const week = dialog.querySelector("[data-week]").value;
    const dates = weekDates(week);
    const loc = dialog.querySelector("[data-location]").value.trim();
    if (!loc) throw Error("Enter the location for this review.");
    if (form.elements.week_start.readOnly && week !== form.elements.week_start.value) throw Error("The selected week differs from the saved baseline.");
    if (form.elements.week_start.min && week < form.elements.week_start.min) throw Error("Choose a following week within the review’s allowed dates.");
    const entries = [], totals = {}, source = [`${short(loc,55)} | ${week} to ${dates[6]}`];
    for (const type of types) {
      const part = section(type), s = state[type];
      if (!part.querySelector("[data-file]").files.length) continue;
      if (!s?.rows) throw Error(reportTypes[type].name + ": finish loading and mapping a valid file.");
      const mapping = Object.fromEntries(Array.from(part.querySelectorAll("[data-field]"), select => [select.dataset.field, Number(select.value)]));
      const selectedLocation = part.querySelector("[data-location-value]")?.value, singleLocation = part.querySelector("[data-single]")?.checked;
      if (selectedLocation && !matchingLocation(selectedLocation) && !part.querySelector("[data-alias]")?.checked) {
        throw Error(reportTypes[type].name + ": confirm that the source location identifies " + loc + ".");
      }
      let result;
      try { result = aggregateReport({ type, rows:s.rows, headerIndex:s.headerIndex, mapping, selectedLocation, singleLocation, week, date1904:s.book.date1904 }); }
      catch (error) { throw Error(reportTypes[type].name + ": " + error.message); }
      const headers = s.rows[s.headerIndex];
      const fieldMap = Object.entries(mapping).filter(([,i])=>i>=0).map(([k,i])=>k+"="+short(headers[i],17)).join(", ");
      source.push(`${type}: ${short(s.file.name,38)}${s.ref ? " ["+s.ref+"]" : ""} / ${short(s.sheet,16)} r${s.headerIndex + 1}; ${short(selectedLocation || loc,22)}; ${result.count} rows (${result.coverage}/7d); ${fieldMap}`);
      entries.push({type,result}); Object.assign(totals,result.totals);
    }
    if (!entries.length) throw Error("Select at least one report.");
    if (!Object.values(totals).some(v => v != null)) throw Error("No complete weekly figures yet. "+entries.map(({type,result})=>reportTypes[type].name+": "+result.gaps.join(". ")).join(" "));
    const omitted = types.filter(t=>!entries.some(e=>e.type===t));
    if (omitted.length) source.push("Reports not supplied: " + omitted.join(", "));
    const reference = source.join("\n");
    if (reference.length > form.elements.source.maxLength && form.elements.source.maxLength !== -1) throw Error("Source references exceed the review field limit. Shorten file names or column headers and try again.");
    return {week,loc,totals,entries,omitted,reference};
  }
  function showPreview() {
    const data = prepare();
    preview = data;
    const list = data.entries.map(({type,result}) => {
      const values = reportTypes[type].fields.map(field => {
        const v = result.totals[field];
        return `<li>${esc(fieldNames[field])}: <strong>${v == null ? "Needs data" : esc(v.toLocaleString("en-US",{maximumFractionDigits:4}))}</strong></li>`;
      }).join("");
      return `<div><h4>${esc(reportTypes[type].name)}</h4><p>${result.count} matching rows across ${result.coverage}/7 dates · ${result.skipped} rows outside scope</p><ul>${values}</ul>${result.gaps.length ? "<p>"+esc(result.gaps.join(". "))+"</p>" : ""}</div>`;
    }).join("");
    dialog.querySelector("[data-result]").innerHTML = `<section><h3>${esc(data.loc)} · ${esc(data.week)}</h3>${list}
      ${data.omitted.length ? "<p>Reports omitted: "+esc(data.omitted.map(t=>reportTypes[t].name).join(", "))+".</p>" : ""}
      <p>Applying replaces the sales and labor fields, including blanks for omitted reports. The labor target is entered separately.</p>
      <button type="button" data-apply class="li-primary">Confirm mapping and use these figures</button></section>`;
    set("[data-feedback]", "Weekly figures are ready to review.");
    dialog.querySelector("[data-apply]").scrollIntoView({block:"nearest"});
  }
  dialog.addEventListener("click", async event => {
    const button = event.target.closest("button");
    if (!button) return;
    try {
      if (button.matches("[data-remove]")) {
        const part = button.closest("[data-report]");
        invalidate(); part.querySelector("[data-file]").value = ""; await loadFile(part.dataset.report,null);
      } else if (button.matches("[data-preview]")) {
        invalidate(); showPreview();
      } else if (button.matches("[data-apply]") && preview) {
        if (!form.isConnected) throw Error("The active review changed. Close this import and open the current review.");
        for (const {fields} of Object.values(reportTypes)) for (const key of fields) form.elements[key].value = preview.totals[key] ?? "";
        form.elements.week_start.value = preview.week;
        form.elements.source.value = preview.reference;
        const status = form.querySelector("[data-import-status]");
        if (status) status.textContent = "Daily reports reconciled. Check the weekly figures, labor target and source references before saving.";
        close();
      }
    } catch (error) { set("[data-feedback]", error.message); }
  });
  dialog.showModal();
}
