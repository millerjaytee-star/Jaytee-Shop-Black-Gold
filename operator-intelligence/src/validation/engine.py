from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from statistics import median

EXPECTED_MONTH_FIELDS = [
    "gross_sales", "discounts", "comps", "refunds", "transactions", "labor_hours",
    "hourly_labor_cost", "management_labor_cost", "overtime_cost", "food_purchases",
    "beginning_inventory", "ending_inventory", "waste_cost", "occupancy_cost",
    "other_operating_cost", "budget_net_sales", "prior_year_net_sales",
    "book_inventory", "physical_inventory",
]


class ValidationResult(dict):
    pass


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate(raw):
    issues = []
    monthly = raw["monthly"]
    weekly = raw["weekly"]
    inventory = raw["inventory"]

    for dataset, rows, key in [("weekly", weekly, "source_record_id"), ("monthly", monthly, "source_record_id")]:
        counts = Counter(row[key] for row in rows)
        for record_id, count in counts.items():
            if count > 1:
                issues.append({"type": "duplicate", "severity": "high", "dataset": dataset, "record_id": record_id, "message": f"{count} copies of {record_id}"})

    for row in monthly:
        for field in EXPECTED_MONTH_FIELDS:
            value = _num(row.get(field))
            if value is None:
                issues.append({"type": "invalid_value", "severity": "high", "dataset": "monthly", "record_id": row["source_record_id"], "field": field, "message": "non-numeric required value"})
            elif value < 0:
                issues.append({"type": "impossible_value", "severity": "high", "dataset": "monthly", "record_id": row["source_record_id"], "field": field, "value": value, "message": "negative value not permitted"})
        try:
            parsed = date.fromisoformat(row["period"])
            if parsed.day != 1:
                issues.append({"type": "period_alignment", "severity": "medium", "dataset": "monthly", "record_id": row["source_record_id"], "period": row["period"], "message": "monthly period not aligned to first day"})
        except (TypeError, ValueError):
            issues.append({"type": "period_alignment", "severity": "high", "dataset": "monthly", "record_id": row["source_record_id"], "period": row.get("period"), "message": "invalid period"})

    by_loc_month = defaultdict(list)
    for row in weekly:
        try:
            parsed = date.fromisoformat(row["week_start"])
        except (TypeError, ValueError):
            continue
        by_loc_month[(row["location_id"], parsed.year, parsed.month)].append(row)

    for key, rows in by_loc_month.items():
        unique = len({row["week_start"] for row in rows})
        if unique < 4:
            issues.append({"type": "missing_period", "severity": "medium", "dataset": "weekly", "location_id": key[0], "period": f"{key[1]:04d}-{key[2]:02d}", "message": f"only {unique}/4 expected weekly periods"})

    monthly_map = {(row["location_id"], row["period"][:7]): row for row in monthly if len(row.get("period", "")) >= 7}
    for key, rows in by_loc_month.items():
        unique_rows = {row["source_record_id"]: row for row in rows}.values()
        ym = f"{key[1]:04d}-{key[2]:02d}"
        month = monthly_map.get((key[0], ym))
        if not month:
            continue
        values = [_num(month[name]) for name in ("gross_sales", "discounts", "comps", "refunds")]
        net = values[0] - values[1] - values[2] - values[3] if None not in values else None
        weekly_sum = sum(_num(row["net_sales"]) or 0 for row in unique_rows)
        if net and abs(weekly_sum / net - 1) > 0.075:
            issues.append({"type": "reconciliation", "severity": "medium", "dataset": "weekly_vs_monthly", "location_id": key[0], "period": ym, "difference_pct": round((weekly_sum / net - 1) * 100, 2), "message": "weekly sales do not reconcile to monthly within tolerance"})

    inventory_map = {(row["location_id"], row["period"]): row for row in inventory}
    for month in monthly:
        inv = inventory_map.get((month["location_id"], month["period"]))
        if not inv:
            continue
        a = _num(month["physical_inventory"])
        b = _num(inv["physical_inventory"])
        if a and b is not None and abs(a - b) / a > 0.02:
            issues.append({"type": "source_conflict", "severity": "medium", "dataset": "inventory", "location_id": month["location_id"], "period": month["period"], "source_a": a, "source_b": b, "message": "physical inventory differs across sources >2%"})

    for row in inventory:
        try:
            period = date.fromisoformat(row["period"])
            count_date = date.fromisoformat(row["count_date"])
            if abs((period - count_date).days) > 62:
                issues.append({"type": "stale_data", "severity": "medium", "dataset": "inventory", "record_id": row["source_record_id"], "period": row["period"], "count_date": row["count_date"], "message": "inventory count is stale relative to reporting period"})
        except (TypeError, ValueError):
            pass

    by_location = defaultdict(list)
    for row in monthly:
        value = _num(row["gross_sales"])
        if value is not None:
            by_location[row["location_id"]].append(value)
    for location_id, values in by_location.items():
        mid = median(values)
        mad = median([abs(value - mid) for value in values]) or 1
        for row in monthly:
            if row["location_id"] != location_id:
                continue
            value = _num(row["gross_sales"])
            if value is not None and abs(value - mid) / mad > 4.5:
                issues.append({"type": "outlier_review", "severity": "low", "dataset": "monthly", "record_id": row["source_record_id"], "field": "gross_sales", "value": value, "message": "statistical outlier; retain unless verified erroneous"})

    counts = Counter(issue["type"] for issue in issues)
    weighted = 100
    caps = {"duplicate": 8, "missing_period": 7, "impossible_value": 12, "period_alignment": 7, "reconciliation": 12, "source_conflict": 8, "stale_data": 7, "outlier_review": 3, "invalid_value": 12}
    for issue_type, count in counts.items():
        weighted -= min(caps.get(issue_type, 8), count * 3)
    weighted = max(0, weighted)
    label = "HIGH" if weighted >= 90 else "MEDIUM" if weighted >= 75 else "LOW" if weighted >= 50 else "INSUFFICIENT DATA"
    return ValidationResult(issues=issues, data_quality_score=weighted, confidence_label=label, issue_counts=dict(counts))
