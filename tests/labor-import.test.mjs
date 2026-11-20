import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { aggregateReport, businessDate, guessMapping, parseDelimited, weekDates } from "../assets/labor-import-data.mjs";

const week = "2026-10-26";
function input(type) {
  const file = new URL("../assets/labor-examples/"+type+".csv", import.meta.url);
  const rows = parseDelimited(readFileSync(file,"utf8"));
  const mapping = guessMapping(type,rows[0]);
  return {type,rows,mapping,headerIndex:0,week,selectedLocation:"Juniper Café"};
}
test("three deidentified daily reports match the independent labor-variance fixture", () => {
  const totals = {};
  for (const type of ["sales","schedule","payroll"]) {
    const result = aggregateReport(input(type));
    assert.equal(result.coverage,7);
    assert.equal(result.count,type==="sales"?7:14);
    assert.deepEqual(result.gaps,[]);
    Object.assign(totals,result.totals);
  }
  assert.deepEqual(totals,{actual_sales:9000,forecast_sales:10000,scheduled_hours:125,scheduled_cost:2500,actual_hours:135,actual_cost:2700});
  assert.equal(totals.actual_cost-totals.actual_sales*.25,450);
});
test("scope excludes other locations and periods; same-day role duplicates fail explicitly", () => {
  const req=input("payroll");
  req.rows.push([week,"Other café","Kitchen",999,9999],["2026-10-25","Juniper Café","Kitchen",99,999]);
  const data=aggregateReport(req);
  assert.equal(data.totals.actual_cost,2700);
  assert.equal(data.skipped,2);
  req.rows.push([...req.rows[1]]);
  assert.throws(()=>aggregateReport(req),/Duplicate 2026-10-26/);
});
test("missing dates and missing fields cannot be mistaken for zero", () => {
  const req=input("sales");
  req.rows[1][3]="";
  assert.deepEqual(aggregateReport(req).totals,{actual_sales:9000,forecast_sales:null});
  req.rows.pop();
  const result=aggregateReport(req);
  assert.deepEqual(result.totals,{actual_sales:null,forecast_sales:null});
  assert.match(result.gaps.join(" "),/Missing dates: 2026-11-01/);
});
test("explicit single-location confirmation, named mappings and valid dates protect totals", () => {
  const req=input("schedule");
  req.mapping.location=-1;
  assert.throws(()=>aggregateReport(req),/confirm the file/);
  req.singleLocation=true;
  assert.equal(aggregateReport(req).totals.scheduled_hours,125);
  req.mapping.scheduled_cost=req.mapping.scheduled_hours;
  assert.throws(()=>aggregateReport(req),/two different fields/);
  req.mapping.scheduled_cost=4;
  req.rows[1][0]="02/30/2026";
  assert.throws(()=>aggregateReport(req),/valid business date/);
});
test("US numeric and date formats, quoted delimiters, embedded newlines, and formulas", () => {
  assert.deepEqual(parseDelimited('Date,Name,Sales\r\n1/2/2026,"Two, ""Cafés""","$1,000.50"\r\n'),[["Date","Name","Sales"],["1/2/2026",'Two, "Cafés"','$1,000.50']]);
  assert.deepEqual(parseDelimited('Date\tName\r\n11/1/2026\t"North\nCafe"'),[["Date","Name"],["11/1/2026","North\nCafe"]]);
  assert.throws(()=>parseDelimited('A,B\n1,"oops'),/quoted/);
  assert.equal(businessDate(1),"1900-01-01");
  assert.equal(businessDate(0,true),"1904-01-01");
  assert.equal(businessDate(60),"");
  assert.equal(weekDates("2026-10-26").at(-1),"2026-11-01");
  const req=input("sales");
  req.rows[1][2]="$1,000.50";
  assert.equal(aggregateReport(req).totals.actual_sales,9000.5);
  req.rows[1][2]="=50+123";
  assert.throws(()=>aggregateReport(req),/Invalid Net sales/);
});
