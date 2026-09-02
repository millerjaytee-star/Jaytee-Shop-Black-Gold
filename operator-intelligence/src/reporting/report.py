from __future__ import annotations


def _money(value):
    return f"${float(value or 0):,.2f}"


def _pct(value):
    return "Not enough data" if value is None else f"{float(value):.1f}%"


def generate(scores, validation, aggregates, priorities, counted, findings):
    """Generate a deterministic analyst-review report from already calculated facts.

    This function does not calculate new opportunity amounts or invent missing data.
    It only renders structured outputs produced by the validated Stabilis engine.
    """
    total = round(sum(float(o.get("realistic_recoverable_opportunity") or 0) for o in counted), 2)
    lines = [
        "# STABILIS OPERATOR INTELLIGENCE — CONTROLLED ANALYSIS",
        "",
        "> Deterministic analysis output. Modeled opportunity is potential, not verified savings. Analyst review is required before customer release.",
        "",
        "## Executive Diagnosis",
        f"- Operator Health Score: {scores.get('operator_health_score', 'Not enough data')}",
        f"- Profit Leak Score: {scores.get('profit_leak_score', 'Not enough data')}",
        f"- Data Quality Score: {validation.get('data_quality_score', 'Not enough data')}",
        f"- Modeled Recoverable Opportunity: {_money(total)}",
        "- Verified Financial Impact: $0.00 in the controlled fictional validation fixture unless separately verified by an intervention/result workflow.",
        "",
        "## Top Priorities",
    ]
    if priorities:
        for idx, item in enumerate(priorities[:5], 1):
            confidence = item.get("confidence") or {}
            lines.extend([
                f"### {idx}. {item.get('location_id', 'Enterprise')} — {item.get('issue_family', 'operating opportunity')}",
                f"- Priority: {item.get('priority_category', 'Not enough data')} ({item.get('priority_score', 'Not enough data')})",
                f"- Modeled Recoverable Opportunity: {_money(item.get('realistic_recoverable_opportunity'))}",
                f"- Confidence: {confidence.get('label', confidence.get('score', 'Not enough data'))}",
                f"- Evidence Finding: {item.get('source_finding_id', 'Not enough data')}",
                f"- Deduplication: {item.get('deduplication_rationale') or 'Primary non-overlapping opportunity.'}",
                "",
            ])
    else:
        lines.extend(["Not enough data to prioritize opportunities.", ""])

    lines.extend(["## Location Performance", ""])
    if aggregates:
        lines.append("| Location | Net Sales | Labor % | Food Cost % | Sales Growth % | Inventory Variance |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
        for location_id, row in sorted(aggregates.items()):
            lines.append(
                f"| {location_id} | {_money(row.get('net_sales'))} | {_pct(row.get('labor_pct'))} | "
                f"{_pct(row.get('food_cost_pct'))} | {_pct(row.get('sales_growth_pct'))} | {_money(row.get('inventory_variance'))} |"
            )
        lines.append("")
    else:
        lines.extend(["Not enough data.", ""])

    lines.extend(["## Findings", ""])
    if findings:
        for finding in findings:
            confidence = finding.get("confidence") or {}
            lines.extend([
                f"### {finding.get('finding_id', 'Finding')} — {finding.get('location_id', 'Enterprise')}",
                f"- Category: {finding.get('issue_family', 'Not enough data')}",
                f"- Metric: {finding.get('metric', 'Not enough data')}",
                f"- Current: {finding.get('current_value', 'Not enough data')}",
                f"- Comparison: {finding.get('comparison_value', 'Not enough data')}",
                f"- Variance: {finding.get('variance', 'Not enough data')}",
                f"- Confidence: {confidence.get('label', confidence.get('score', 'Not enough data'))}",
                "",
            ])
    else:
        lines.extend(["No material operating findings were produced.", ""])

    lines.extend([
        "## Data Quality",
        f"- Score: {validation.get('data_quality_score', 'Not enough data')}",
        f"- Confidence Label: {validation.get('confidence_label', 'Not enough data')}",
        f"- Issue Counts: {validation.get('issue_counts', {})}",
        "",
        "## Methodology / Financial Stage",
        "- Calculations, scores and modeled opportunity values are deterministic and versioned.",
        "- Supporting evidence does not add to the canonical opportunity rollup unless proven additive.",
        "- Modeled Opportunity ≠ Action Underway ≠ Observed Improvement ≠ Verified Financial Impact.",
        "- Missing evidence remains `Not enough data`; this report does not fill gaps with generated estimates.",
        "",
    ])
    return "\n".join(lines)
