import Foundation

@MainActor
final class FictionalWorkspace {
    static let managerID = UUID(uuidString: "00000000-0000-4000-8000-000000000014")!
    private static let organizationID = UUID(uuidString: "00000000-0000-4000-8000-000000000011")!
    private static let locationID = UUID(uuidString: "00000000-0000-4000-8000-000000000012")!
    private static let reviewID = UUID(uuidString: "00000000-0000-4000-8000-000000000013")!
    private let storageKey = "stabilis-ios-fictional-review-v1"

    static let baseline: [String: Double?] = [
        "forecast_sales": 10_000, "actual_sales": 9_000, "target_pct": 25,
        "scheduled_hours": 125, "actual_hours": 135, "scheduled_cost": 2_500, "actual_cost": 2_700
    ]
    static let followingWeek: [String: Double?] = [
        "forecast_sales": 10_000, "actual_sales": 9_500, "target_pct": 25,
        "scheduled_hours": 125, "actual_hours": 125, "scheduled_cost": 2_500, "actual_cost": 2_500
    ]

    var review: Review {
        if let data = UserDefaults.standard.data(forKey: storageKey),
           let review = try? JSONDecoder().decode(Review.self, from: data), review.id == Self.reviewID {
            return review
        }
        return Review(id: Self.reviewID, organizationId: Self.organizationID, locationId: Self.locationID,
                      weekStart: "2026-11-02", status: "released", source: "Fictional Juniper Café sales, schedule and payroll exports", version: 1,
                      inputs: Self.baseline, metrics: Self.metrics(Self.baseline), action: nil, followup: nil, verification: nil)
    }

    func save(_ original: Review, role: DemoRole, operation: String, payload: [String: JSONValue]) throws -> Review {
        guard review.id == original.id, review.version == original.version else {
            throw FictionalReviewError("This review changed. Return to the list and try again.")
        }
        var status = original.status
        var action = original.action ?? [:]
        var followup = original.followup
        let date = Date().ISO8601Format()

        switch operation {
        case "assign" where role == .owner && ["released", "change_requested"].contains(status):
            guard let due = payload["due_date"]?.labelText, let next = payload["next_review"]?.labelText,
                  due >= original.weekStart, next >= due else {
                throw FictionalReviewError("Choose a due date and a later review date.")
            }
            action = payload
            action["approved_at"] = .string(date)
            action["assignee_id"] = .string(Self.managerID.uuidString)
            action["assignee_name"] = .string("Morgan Ellis")
            status = "assigned"
        case "accept" where role == .manager && status == "assigned":
            action["accepted_at"] = .string(date)
            status = "accepted"
        case "request_change" where role == .manager && status == "assigned":
            action["change_note"] = payload["note"]
            status = "change_requested"
        case "submit_evidence" where role == .manager && status == "accepted":
            action["evidence"] = payload["note"]
            action["clarification"] = nil
            action["evidence_at"] = .string(date)
            status = "evidence_submitted"
        case "clarify" where role == .owner && status == "evidence_submitted":
            action["clarification"] = payload["note"]
            action["evidence"] = nil
            status = "accepted"
        case "compare" where role == .owner && ["evidence_submitted", "compared"].contains(status):
            let inputs = (payload["inputs"]?.fields ?? [:]).mapValues { $0.finiteNumber }
            let result = Self.metrics(inputs)
            followup = payload
            followup?["metrics"] = .object(result.mapValues { value in value.map(JSONValue.number) ?? .null })
            if payload["comparable"]?.flag == true, let start = original.metrics["total_over"] ?? nil,
               let end = result["total_over"] ?? nil {
                followup?["observed_change"] = .number(start - end)
            }
            status = "compared"
        case "reopen" where role == .owner && ["evidence_submitted", "compared"].contains(status):
            followup = nil
            action["evidence"] = nil
            action["clarification"] = payload["note"]
            status = "accepted"
        default:
            throw FictionalReviewError("Choose the assigned role to take this step.")
        }

        let saved = Review(id: original.id, organizationId: original.organizationId, locationId: original.locationId,
                           weekStart: original.weekStart, status: status, source: original.source, version: original.version + 1,
                           inputs: original.inputs, metrics: original.metrics, action: action, followup: followup, verification: nil)
        UserDefaults.standard.set(try JSONEncoder().encode(saved), forKey: storageKey)
        return saved
    }

    func reset() {
        UserDefaults.standard.removeObject(forKey: storageKey)
    }

    // The database calculates customer reviews. This calculation is for fictional inputs.
    private static func metrics(_ input: [String: Double?]) -> [String: Double?] {
        let forecast = input["forecast_sales"] ?? nil
        let sales = input["actual_sales"] ?? nil
        let target = (input["target_pct"] ?? nil).map { $0 / 100 }
        let scheduled = input["scheduled_cost"] ?? nil
        let paid = input["actual_cost"] ?? nil
        let scheduledHours = input["scheduled_hours"] ?? nil
        let paidHours = input["actual_hours"] ?? nil
        let rate = sales.flatMap { sales in sales > 0 ? paid.map { $0 / sales } : nil }
        func difference(_ first: Double?, _ second: Double?) -> Double? {
            first.flatMap { a in second.map { a - $0 } }
        }
        func product(_ first: Double?, _ second: Double?) -> Double? {
            first.flatMap { a in second.map { a * $0 } }
        }
        let result = [
            "actual_pct": rate.map { $0 * 100 },
            "points_over": difference(rate, target).map { $0 * 100 },
            "hours_over": difference(paidHours, scheduledHours),
            "schedule_effect": difference(scheduled, product(target, forecast)),
            "sales_effect": product(target, difference(forecast, sales)),
            "payroll_effect": difference(paid, scheduled),
            "total_over": difference(paid, product(target, sales))
        ]
        return result.mapValues { $0.map { ($0 * 100).rounded() / 100 } }
    }
}

private struct FictionalReviewError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}
