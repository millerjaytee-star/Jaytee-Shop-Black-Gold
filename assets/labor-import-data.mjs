/** Map daily, deidentified reports to one seven-day location review. No storage or network access. */
export const reportTypes = {
  sales: { name: "Sales", fields: ["actual_sales", "forecast_sales"] },
  schedule: { name: "Approved schedule", fields: ["scheduled_hours", "scheduled_cost"] },
  payroll: { name: "Paid labor", fields: ["actual_hours", "actual_cost"] },
};
export const fieldNames = {
  date: "Business date", location: "Location", role: "Role or department",
  actual_sales: "Net sales ($)", forecast_sales: "Forecast net sales ($)",
  scheduled_hours: "Scheduled hours", scheduled_cost: "Scheduled labor ($)",
  actual_hours: "Paid hours", actual_cost: "Paid labor ($)",
};
const aliases = {
  date: ["date", "business date", "trading date", "work date", "shift date"],
  location: ["location", "site", "site name", "store", "store name", "location id", "location name", "unit"],
  role: ["role", "position", "department", "job", "job title", "job code"],
  actual_sales: ["net sales", "actual net sales", "actual sales", "net sales dollars"],
  forecast_sales: ["forecast sales", "sales forecast", "forecast net sales", "planned sales"],
  scheduled_hours: ["scheduled hours", "approved scheduled hours", "sched hours", "planned hours"],
  scheduled_cost: ["scheduled cost", "scheduled labor dollars", "scheduled labor cost", "scheduled wages", "scheduled pay"],
  actual_hours: ["paid hours", "actual paid hours", "actual hours", "hours paid", "total hours"],
  actual_cost: ["paid labor cost", "paid labor", "actual cost", "actual paid labor", "actual labor dollars", "gross pay", "labor cost"],
};
function normalize(value) {
  return String(value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
export function fieldsFor(type) {
  return ["date", "location", ...(type === "sales" ? [] : ["role"]), ...reportTypes[type].fields];
}
export function guessMapping(type, headers) {
  return Object.fromEntries(fieldsFor(type).map(key => {
    const matches = headers.reduce((found, value, i) => {
      if (aliases[key].includes(normalize(value))) found.push(i);
      return found;
    }, []);
    return [key, matches.length === 1 ? matches[0] : -1];
  }));
}

export function parseDelimited(text) {
  text = text.replace(/^\uFEFF/, "");
  // Prefer the delimiter that actually separates the first nonempty record outside quotes.
  const candidates = [",", "\t", ";"];
  const counts = [0, 0, 0];
  let inQuotes = false;
  for (const char of text.trimStart()) {
    if (char === '"') inQuotes = !inQuotes;
    if (inQuotes) continue;
    if (char === "\n" || char === "\r") break;
    const index = candidates.indexOf(char);
    if (index >= 0) counts[index]++;
  }
  const delimiter = candidates[counts.indexOf(Math.max(...counts))];
  const rows = [];
  let row = [], value = "", quoted = false, endQuote = false;
  const pushValue = () => { row.push(value.trim()); value = ""; endQuote = false; };
  const pushRow = () => {
    pushValue();
    if (row.some(Boolean)) rows.push(row);
    if (rows.length > 15000 || row.length > 256) throw Error("Choose an export with at most 15,000 rows and 256 columns.");
    row = [];
  };
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char !== '"') value += char;
      else if (text[i + 1] === '"') { value += '"'; i++; }
      else { quoted = false; endQuote = true; }
    } else if (char === delimiter) {
      pushValue();
      if (row.length >= 256) throw Error("Choose an export with at most 256 columns.");
    } else if (char === "\n" || char === "\r") {
      if (char === "\r" && text[i + 1] === "\n") i++;
      pushRow();
    } else if (char === '"' && !value.trim() && !endQuote) {
      value = ""; quoted = true;
    } else if ((endQuote && char.trim()) || char === '"') {
      throw Error("Invalid quoted field in the delimited export.");
    } else value += char;
  }
  if (quoted) throw Error("The export ends inside a quoted field.");
  if (row.length || value || endQuote) pushRow();
  return rows;
}

function fromDateParts(year, month, day) {
  const d = new Date(Date.UTC(year, month - 1, day));
  if (year < 1900 || year > 2199 || d.getUTCMonth() !== month - 1 || d.getUTCDate() !== day) return "";
  return d.toISOString().slice(0, 10);
}
export function businessDate(value, date1904 = false) {
  if (typeof value === "number") {
    const serial = Math.floor(value);
    if (!Number.isFinite(value) || serial < (date1904 ? 0 : 1) || serial > 110000 || (!date1904 && serial === 60)) return "";
    const epoch = date1904 ? Date.UTC(1904, 0, 1) : Date.UTC(1899, 11, serial < 60 ? 31 : 30);
    return new Date(epoch + serial * 86400000).toISOString().slice(0, 10);
  }
  const s = String(value ?? "").trim();
  let m = /^(\d{4})-(\d{1,2})-(\d{1,2})(?:T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)?)?$/.exec(s);
  if (m) return fromDateParts(Number(m[1]), Number(m[2]), Number(m[3]));
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s);
  return m ? fromDateParts(Number(m[3]), Number(m[1]), Number(m[2])) : "";
}
export function weekDates(start) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(start) || businessDate(start) !== start) throw Error("Choose a valid fiscal week start date.");
  return Array.from({length:7}, (_, i) => new Date(Date.parse(start + "T00:00:00Z") + i * 86400000).toISOString().slice(0, 10));
}
function numeric(value, field) {
  if (typeof value === "number") return Number.isFinite(value) ? value : NaN;
  let s = String(value ?? "").trim();
  if (!s) return null;
  if (/^\(.*\)$/.test(s)) s = "-" + s.slice(1, -1);
  // CSV currency conventions are US dollars. Reject malformed grouping and locale ambiguity.
  if (!/^-?\$?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$/.test(s)) return NaN;
  if (field.endsWith("hours") && s.includes("$")) return NaN;
  return Number(s.replace(/[$,]/g, ""));
}

export function aggregateReport({type, rows, headerIndex, mapping, selectedLocation, singleLocation, week, date1904 = false}) {
  const { fields } = reportTypes[type];
  const days = weekDates(week);
  const mapped = fields.filter(k => Number.isInteger(mapping[k]) && mapping[k] >= 0);
  if (!Number.isInteger(headerIndex) || headerIndex < 0 || !rows[headerIndex]) throw Error("Select a header row.");
  if (!Number.isInteger(mapping.date) || mapping.date < 0) throw Error("Map a business-date column.");
  if (!mapped.length) throw Error("Map at least one report amount or hours column.");
  if (mapping.location >= 0 && !String(selectedLocation ?? "").trim()) throw Error("Choose the source location to include.");
  if (!(mapping.location >= 0) && !singleLocation) throw Error("Map a location column or confirm the file contains only the selected location.");
  const assigned = fieldsFor(type).map(k => mapping[k]).filter(i => i >= 0);
  if (new Set(assigned).size !== assigned.length) throw Error("A column cannot supply two different fields.");
  if (assigned.some(i => i >= rows[headerIndex].length || !String(rows[headerIndex][i] ?? "").trim())) throw Error("Map named source columns only.");
  const matchedDays = new Set();
  const seen = new Set();
  const sums = Object.fromEntries(mapped.map(k => [k, 0]));
  const missingCells = new Set();
  let count = 0, skipped = 0;
  for (let n = headerIndex + 1; n < rows.length; n++) {
    const r = rows[n];
    if (!r.some(v => String(v ?? "").trim())) continue;
    const rowNo = n + 1;
    if (mapping.location >= 0 && String(r[mapping.location] ?? "").trim() !== selectedLocation) { skipped++; continue; }
    const date = businessDate(r[mapping.date], date1904);
    if (!date) throw Error("Row " + rowNo + " has no valid business date. Use YYYY-MM-DD, US M/D/YYYY, or an Excel date.");
    if (!days.includes(date)) { skipped++; continue; }
    const roleValue = mapping.role >= 0 ? String(r[mapping.role] ?? "").trim() : "";
    if (mapping.role >= 0 && !roleValue) throw Error("Row " + rowNo + " is missing its role. Remove subtotal rows or correct the role.");
    if (/^(?:grand )?(?:total|subtotal|all roles|all departments)$/i.test(roleValue)) throw Error("Row " + rowNo + " is a subtotal. Remove totals when using detail rows.");
    const key = date + "\u0000" + roleValue.toLowerCase();
    if (seen.has(key)) throw Error("Duplicate " + date + (roleValue ? " / " + roleValue : "") + " at row " + rowNo + ". Use daily totals or map a distinct role on each labor row.");
    seen.add(key); matchedDays.add(date); count++;
    for (const k of mapped) {
      const v = numeric(r[mapping[k]], k);
      if (v === null) { missingCells.add(k); continue; }
      if (!Number.isFinite(v) || Math.abs(v) > 1e10 || (!k.endsWith("sales") && v < 0)) throw Error("Invalid " + fieldNames[k] + " at row " + rowNo + ". Correct the source value.");
      sums[k] += v;
    }
  }
  if (!count) throw Error("No rows match this location and fiscal week.");
  const missingDays = days.filter(d => !matchedDays.has(d));
  const gaps = [];
  const totals = {};
  for (const k of fields) {
    if (!mapped.includes(k)) gaps.push(fieldNames[k] + " unmapped");
    else if (missingCells.has(k)) gaps.push(fieldNames[k] + " contains blanks");
    else if (sums[k] < 0) throw Error("Net weekly " + fieldNames[k] + " is negative. Review the report before importing.");
    totals[k] = !mapped.includes(k) || missingCells.has(k) || missingDays.length ? null : Math.round(sums[k] * 10000) / 10000;
  }
  if (missingDays.length) gaps.push("Missing dates: " + missingDays.join(", ") + ". Supply zero rows for verified closed days.");
  return { totals, gaps, count, skipped, coverage: matchedDays.size };
}
