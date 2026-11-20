type WeeklyLaborReview = {
  id: string;
  week_start: string;
  status: string;
  metrics?: {
    actual_pct?: number | null;
    hours_over?: number | null;
    schedule_effect?: number | null;
    sales_effect?: number | null;
    payroll_effect?: number | null;
    total_over?: number | null;
  };
  followup?: { comparable?: boolean; observed_change?: number | null } | null;
  verification?: { amount?: number | null } | null;
};

const currency = new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 2,
});
const weekDate = /\b\d{4}-\d{2}-\d{2}\b/;
const releasedStates = new Set(["released", "assigned", "accepted", "change_requested", "evidence_submitted", "compared", "verified"]);

export function isWeeklyLaborQuestion(question: string) {
  return /\b(labor|labour|payroll|schedule|staffing)\b/i.test(question) &&
    (/\b(week|weekly|variance|over target|plan|forecast|paid hours)\b/i.test(question) || weekDate.test(question));
}

export function explainWeeklyLaborReview(question: string, records: WeeklyLaborReview[], locationId: string) {
  const requestedWeek = question.match(weekDate)?.[0];
  const record = (records || []).find(row => releasedStates.has(row.status) && (!requestedWeek || row.week_start === requestedWeek));
  if (!record) return null;

  const metrics = record.metrics || {};
  const details: string[] = [];
  const missing: string[] = [];
  const add = (amount: number | null | undefined, label: string, source: string) => {
    if (amount == null) missing.push(source);
    else details.push(`${label} was ${currency.format(amount)}`);
  };

  let baseline = "The historical labor variance needs actual sales, paid labor cost and the labor target.";
  if (metrics.total_over != null) {
    const outcome = metrics.total_over > 0 ? "above target" : "below target";
    baseline = metrics.total_over === 0 ? "Actual labor dollars were on target." :
      `Actual labor dollars were ${currency.format(Math.abs(metrics.total_over))} ${outcome} at actual sales.`;
  } else {
    missing.push("actual sales, paid labor dollars and the labor target to explain the total");
  }

  add(metrics.schedule_effect,"Schedule against its forecast budget","approved schedule cost, forecast sales and the labor target");
  add(metrics.sales_effect,"Sales effect","forecast sales, actual sales and the labor target");
  add(metrics.payroll_effect,"Paid labor against schedule","scheduled and paid labor dollars");
  const context = [
    metrics.actual_pct == null ? "" : `Actual labor was ${metrics.actual_pct}% of net sales.`,
    metrics.hours_over == null ? "" : metrics.hours_over === 0 ? "Paid hours matched the schedule." :
      `Paid hours were ${Math.abs(metrics.hours_over)} ${metrics.hours_over > 0 ? "above" : "below"} schedule.`,
  ].filter(Boolean).join(" ");
  const change = record.followup?.observed_change;
  const observed = !record.followup ? "Awaiting comparison." : !record.followup.comparable ?
    "The weeks were marked incomparable." : change == null ? "Comparable dollars are unavailable." : `${currency.format(change)}.`;
  const verification = record.status === "verified" ? record.verification?.amount : null;

  return {
    answer: [
      `Week starting ${record.week_start}. ${baseline}`,
      context,
      details.length ? `${details.join(". ")}. Positive components increase the variance.` : "",
      "Check shift evidence with the GM before attributing the variance to a specific cause.",
      "Modeled opportunity. No approved estimate in this weekly record.",
      `Observed change. ${observed}`,
      `Client-verified financial impact. ${verification == null ? "No finance validation recorded." : currency.format(verification) + "."}`,
    ].filter(Boolean).join("\n\n"),
    confidence: missing.length ? "INSUFFICIENT" : "HIGH",
    data_gap: missing.length > 0,
    missing_data: missing,
    evidence: [{ id: record.id, type: "weekly_labor_review", label: "Released labor review", location_id: locationId, period: record.week_start }],
    recommendation_draft: null,
  };
}
