import Foundation

struct LaborInputField {
    enum Unit { case dollars, percent, hours }

    let key: String
    let name: String
    let unit: Unit

    func format(_ value: Double?) -> String {
        guard let value else { return "Needs data" }
        switch unit {
        case .dollars: return reviewMoney(value)
        case .percent: return "\(reviewNumber(value))%"
        case .hours: return "\(reviewNumber(value)) hr"
        }
    }
}

struct LaborVariancePart {
    let key: String
    let name: String
    let value: Double?
    let equation: String
}

extension Review {
    static let fields = [
        LaborInputField(key: "forecast_sales", name: "Forecast net sales", unit: .dollars),
        LaborInputField(key: "actual_sales", name: "Actual net sales", unit: .dollars),
        LaborInputField(key: "target_pct", name: "Labor target", unit: .percent),
        LaborInputField(key: "scheduled_hours", name: "Scheduled hours", unit: .hours),
        LaborInputField(key: "actual_hours", name: "Actual paid hours", unit: .hours),
        LaborInputField(key: "scheduled_cost", name: "Scheduled labor", unit: .dollars),
        LaborInputField(key: "actual_cost", name: "Actual paid labor", unit: .dollars)
    ]

    func input(_ key: String) -> Double? { inputs[key] ?? nil }
    func metric(_ key: String) -> Double? { metrics[key] ?? nil }
    func actionText(_ key: String) -> String? { action?[key]?.labelText }

    var total: Double? { metric("total_over") }
    var followupTotal: Double? { followup?["metrics"]?.fields?["total_over"]?.finiteNumber }
    var observed: Double? { followup?["observed_change"]?.finiteNumber }

    var statusLabel: String {
        ["draft": "Awaiting analyst release", "released": "Ready for owner decision", "assigned": "Awaiting GM acceptance",
         "accepted": "Action in progress", "change_requested": "Change requested", "evidence_submitted": "Evidence submitted",
         "compared": "Following week reviewed", "verified": "Finance validated"][status] ?? "Review available"
    }

    var isOverdue: Bool {
        guard ["assigned", "accepted", "change_requested"].contains(status), let due = actionText("due_date") else { return false }
        return due < WeekDate.iso(Date())
    }

    var varianceLabel: String {
        guard let total else { return "Labor cost, net sales and the labor target are needed to measure total variance." }
        if total == 0 { return "On target at actual sales" }
        return total > 0 ? "Over target at actual sales" : "Under target at actual sales"
    }

    var summary: String? {
        var findings: [String] = []
        if let forecast = input("forecast_sales"), let actual = input("actual_sales") {
            let difference = actual - forecast
            findings.append(difference == 0 ? "Net sales matched forecast." : "Net sales were \(reviewMoney(abs(difference))) \(difference < 0 ? "below" : "above") forecast.")
        }
        if let hours = metric("hours_over") {
            findings.append(hours == 0 ? "Paid hours matched the schedule." : "Paid labor was \(reviewNumber(abs(hours))) hours \(hours > 0 ? "over" : "under") schedule.")
        }
        return findings.isEmpty ? nil : findings.joined(separator: " ")
    }

    var varianceParts: [LaborVariancePart] {
        let forecast = reviewMoney(input("forecast_sales"))
        let sales = reviewMoney(input("actual_sales"))
        let scheduled = reviewMoney(input("scheduled_cost"))
        let paid = reviewMoney(input("actual_cost"))
        let target = "\(reviewNumber(input("target_pct")))%"
        return [
            part("schedule_effect", "Schedule against forecast budget", "\(scheduled) − (\(target) × \(forecast))"),
            part("sales_effect", "Sales effect against forecast", "\(target) × (\(forecast) − \(sales))"),
            part("payroll_effect", "Paid labor against schedule", "\(paid) − \(scheduled)")
        ]
    }

    var totalEquation: String {
        part("total_over", "Total at actual sales", "\(reviewMoney(input("actual_cost"))) − (\(reviewNumber(input("target_pct")))% × \(reviewMoney(input("actual_sales")))").equation
    }

    private func part(_ key: String, _ name: String, _ formula: String) -> LaborVariancePart {
        let value = metric(key)
        return LaborVariancePart(key: key, name: name, value: value, equation: value.map { "\(formula) = \(reviewMoney($0))" } ?? "Needs data")
    }

    var observedLabel: String {
        guard let followup else { return "Awaiting comparison" }
        if followup["comparable"]?.flag != true { return "Periods incomparable" }
        return reviewMoney(observed)
    }

    var followupOutcome: String? {
        guard followup != nil else { return nil }
        guard followup?["comparable"]?.flag == true else { return "Different operating conditions limit the comparison." }
        guard let observed else { return "Provide labor cost, net sales and labor targets for both weeks to measure the change." }
        if observed == 0 { return "Labor variance stayed flat after the action." }
        if observed < 0 { return "The action has evidence. Labor variance worsened by \(reviewMoney(-observed))." }
        return "Labor variance improved by \(reviewMoney(observed))."
    }

    func verifiedLabel(demo: Bool) -> String {
        if let amount = verification?["amount"]?.finiteNumber { return reviewMoney(amount) }
        return demo ? "$0 · No finance validation" : "No finance validation"
    }

    func shareText(location: String, demo: Bool) -> String {
        var lines = [
            "Stabilis Operator Intelligence™ · Weekly labor review", demo ? "Fictional · \(location)" : location,
            "Week of \(WeekDate.display(weekStart))", statusLabel, "",
            "Historical variance: \(reviewMoney(total))", "Baseline source: \(source)"
        ]
        lines += varianceParts.map { "\($0.name): \(reviewMoney($0.value))" }
        lines += ["", "Modeled opportunity: No approved estimate", "Following-week variance: \(reviewMoney(followupTotal))",
                  "Observed change: \(observedLabel)", "Client-verified financial impact: \(verifiedLabel(demo: demo))"]
        if let outcome = followupOutcome { lines.append(outcome) }
        if let title = actionText("title") {
            lines += ["", "Decision: \(title)"]
            for (key, label) in [("assignee_name", "Responsible manager"), ("due_date", "Due date"), ("next_review", "Next review"), ("target_measure", "Target measure"), ("evidence_required", "Evidence required"), ("evidence", "Evidence"), ("clarification", "Open question")] {
                if let value = actionText(key) { lines.append("\(label): \(value)") }
            }
        }
        return lines.joined(separator: "\n")
    }
}
