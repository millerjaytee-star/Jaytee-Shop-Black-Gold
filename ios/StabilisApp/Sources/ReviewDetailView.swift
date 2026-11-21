import SwiftUI

struct ReviewDetailView: View {
    let id: UUID
    @ObservedObject var store: WorkspaceStore
    @State private var editor: ReviewEditor?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 15) {
                if let review = store.reviews.first(where: { $0.id == id }) {
                    heading(review)
                    if let error = store.error { WorkspaceMessage(text: error, isError: true) }
                    if let notice = store.notice { WorkspaceMessage(text: notice) }
                    if store.saving { ProgressView("Saving review…") }

                    if store.isAssignedManager(review) { actionCard(review) }
                    varianceCard(review)
                    if !store.isAssignedManager(review) { actionCard(review) }
                    resultsCard(review)
                    exportCard(review)
                } else if store.busy {
                    ProgressView("Opening weekly review…")
                } else {
                    ContentUnavailableView("Review unavailable", systemImage: "lock.shield", description: Text("Ask your workspace administrator to confirm your location access."))
                }
            }
            .frame(maxWidth: 700)
            .padding(18)
            .frame(maxWidth: .infinity)
        }
        .background(StabilisStyle.paper.ignoresSafeArea())
        .foregroundStyle(StabilisStyle.ink)
        .navigationTitle("Weekly labor review")
        .navigationBarTitleDisplayMode(.inline)
        .refreshable { await store.refresh() }
        .toolbar {
            if store.isDemo {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        ForEach(DemoRole.allCases) { role in
                            Button { store.setDemoRole(role) } label: {
                                if role == store.demoRole { Label(role.label, systemImage: "checkmark") }
                                else { Text(role.label) }
                            }
                        }
                    } label: {
                        Label("Fictional role", systemImage: "person.crop.circle")
                            .labelStyle(.iconOnly)
                    }
                    .accessibilityIdentifier("demo.detailRole")
                    .disabled(store.saving)
                }
            }
        }
        .sheet(item: $editor) { editor in
            if let review = store.reviews.first(where: { $0.id == id }) {
                ReviewEditorView(store: store, review: review, editor: editor)
            }
        }
    }

    private func heading(_ review: Review) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(store.isDemo ? "Fictional · \(store.locationName)" : store.locationName)
                .font(.subheadline.weight(.semibold)).foregroundStyle(StabilisStyle.secondary)
            Text("Week of \(WeekDate.display(review.weekStart))")
                .font(.system(.title, design: .serif).weight(.semibold))
                .accessibilityAddTraits(.isHeader)
            Text(store.isDemo ? "\(store.demoRole.label) · \(review.statusLabel)" : review.statusLabel)
                .font(.subheadline).foregroundStyle(StabilisStyle.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func varianceCard(_ review: Review) -> some View {
        let values = review.varianceParts
        let denominator = values.map { abs($0.value ?? 0) }.reduce(0, +)
        return StabilisCard {
            VStack(alignment: .leading, spacing: 12) {
                Text("Historical variance").font(.headline).accessibilityAddTraits(.isHeader)
                Text(reviewMoney(review.total.map(abs)))
                    .font(.system(.largeTitle, design: .serif).weight(.semibold)).monospacedDigit()
                    .accessibilityIdentifier("review.historicalVariance")
                Text(review.varianceLabel).foregroundStyle(StabilisStyle.secondary)
                if let summary = review.summary { Text(summary).font(.subheadline) }

                ForEach(values, id: \.key) { part in
                    VStack(alignment: .leading, spacing: 5) {
                        ReviewRow(label: part.name, value: reviewMoney(part.value))
                        if let value = part.value, denominator > 0 {
                            ProgressView(value: abs(value) / denominator)
                                .tint(StabilisStyle.accent)
                                .accessibilityHidden(true)
                        }
                    }
                }

                Divider().overlay(StabilisStyle.rule)
                ReviewRow(label: "Actual labor", value: review.metric("actual_pct").map { "\(reviewNumber($0))%" } ?? "Unavailable")
                ReviewRow(label: "Labor vs. target", value: review.metric("points_over").map { "\(reviewNumber($0)) percentage points" } ?? "Unavailable")
                ReviewRow(label: "Hours vs. schedule", value: review.metric("hours_over").map { "\(reviewNumber($0)) hr" } ?? "Needs data")

                if review.input("actual_sales") == 0 {
                    WorkspaceMessage(text: "Sales were $0. Labor percentage is unavailable. The dollar comparison still uses recorded sales and payroll.")
                }
                if review.input("forecast_sales") == nil {
                    WorkspaceMessage(text: "Add the forecast for this location and week to separate the sales effect from the schedule budget.")
                }
                DisclosureGroup("Show the math and sources") {
                    VStack(alignment: .leading, spacing: 10) {
                        ForEach(values, id: \.key) { part in
                            ReviewRow(label: part.name, value: part.equation)
                        }
                        ReviewRow(label: "Total at actual sales", value: review.totalEquation)
                        Text(verbatim: review.source).font(.subheadline)
                    }
                    .padding(.top, 10)
                }
                .padding(.vertical, 6)
                .accessibilityIdentifier("review.math")
            }
        }
    }

    private func actionCard(_ review: Review) -> some View {
        StabilisCard {
            VStack(alignment: .leading, spacing: 12) {
                Text(store.isAssignedManager(review) ? "Your assigned action" : "Action and follow-through")
                    .font(.headline).accessibilityAddTraits(.isHeader)
                if let title = review.actionText("title") {
                    Text(verbatim: title).font(.title3.weight(.semibold))
                    actionRows(review)
                } else {
                    Text(review.status == "draft" ? "This finding awaits analyst release." : "The location needs an owner decision and an assigned manager.")
                        .font(.subheadline).foregroundStyle(StabilisStyle.secondary)
                }
                if review.isOverdue { WorkspaceMessage(text: "Action overdue.", isError: true) }
                if store.role == "GENERAL_MANAGER", review.actionText("title") != nil, !store.isAssignedManager(review) {
                    Text("Only the assigned general manager can respond or submit evidence.")
                        .font(.subheadline).foregroundStyle(StabilisStyle.secondary)
                }
                actionButtons(review)
            }
        }
    }

    @ViewBuilder private func actionRows(_ review: Review) -> some View {
        ReviewRow(label: "Responsible manager", value: review.actionText("assignee_name") ?? "Pending")
        if let due = review.actionText("due_date") { ReviewRow(label: "Due date", value: WeekDate.display(due)) }
        if let next = review.actionText("next_review") { ReviewRow(label: "Next review", value: WeekDate.display(next)) }
        if let measure = review.actionText("target_measure") { ReviewRow(label: "Target measure", value: measure) }
        if let required = review.actionText("evidence_required") { ReviewRow(label: "Evidence to submit", value: required) }
        if let acceptedAt = review.actionText("accepted_at") { ReviewRow(label: "Accepted", value: WeekDate.display(acceptedAt)) }
        if let requested = review.actionText("change_note") { ReviewRow(label: "Change requested", value: requested) }
        if let clarification = review.actionText("clarification") { ReviewRow(label: "Clarification requested", value: clarification) }
        if let evidence = review.actionText("evidence") { ReviewRow(label: "Submitted evidence", value: evidence) }
    }

    @ViewBuilder private func actionButtons(_ review: Review) -> some View {
        if store.canAssign && ["released", "change_requested"].contains(review.status) {
            if store.assignees.isEmpty {
                WorkspaceMessage(text: "No enrolled manager is available for this location. Check the roster with your workspace administrator.")
            } else {
                editorButton("Approve and assign", open: .assign, id: "review.assign")
            }
        } else if store.isAssignedManager(review), review.status == "assigned" {
            Text("Accept to confirm the listed due date and next review.").font(.subheadline).foregroundStyle(StabilisStyle.secondary)
            Button("Accept action") { Task { _ = await store.save(review, operation: "accept") } }
                .buttonStyle(StabilisButtonStyle())
                .disabled(store.saving || store.busy)
                .accessibilityIdentifier("review.accept")
            editorButton("Request a change", open: .change, id: "review.change", primary: false)
        } else if store.isAssignedManager(review), review.status == "accepted" {
            editorButton("Record completion evidence", open: .evidence, id: "review.evidence")
        } else if store.canReviewEvidence, review.status == "evidence_submitted" {
            editorButton("Review evidence and compare", open: .compare, id: "review.compare")
            editorButton("Request clarification", open: .clarify, id: "review.clarify", primary: false)
        } else if store.canReviewEvidence, ["compared", "verified"].contains(review.status) {
            editorButton("Reopen action", open: .reopen, id: "review.reopen", primary: false)
        }
    }

    private func editorButton(_ label: String, open: ReviewEditor, id: String, primary: Bool = true) -> some View {
        Button(label) { editor = open }
            .buttonStyle(StabilisButtonStyle(primary: primary))
            .disabled(store.saving || store.busy)
            .accessibilityIdentifier(id)
    }

    private func resultsCard(_ review: Review) -> some View {
        StabilisCard {
            VStack(alignment: .leading, spacing: 12) {
                Text("Results").font(.headline).accessibilityAddTraits(.isHeader)
                ReviewRow(label: "Modeled opportunity", value: "No approved estimate")
                ReviewRow(label: "Baseline variance", value: reviewMoney(review.total))
                ReviewRow(label: "Following-week variance", value: review.followup == nil ? "Awaiting review" : reviewMoney(review.followupTotal))
                ReviewRow(label: "Observed change", value: review.observedLabel)
                    .accessibilityIdentifier("review.observedChange")
                ReviewRow(label: "Client-verified financial impact", value: review.verifiedLabel(demo: store.isDemo))
                if let source = review.followup?["source"]?.labelText { Text(verbatim: source).font(.subheadline) }
                if let note = review.followup?["note"]?.labelText { Text(verbatim: note).font(.subheadline) }
                if let outcome = review.followupOutcome { Text(verbatim: outcome).font(.subheadline.weight(.semibold)) }
                if let inputs = review.followup?["inputs"]?.fields {
                    DisclosureGroup("Compare planned and actual figures") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Baseline → following week").font(.subheadline).foregroundStyle(StabilisStyle.secondary)
                            ForEach(Review.fields, id: \.key) { field in
                                ReviewRow(label: field.name, value: "\(field.format(review.input(field.key))) → \(field.format(inputs[field.key]?.finiteNumber))")
                            }
                        }
                        .padding(.top, 10)
                    }
                    .padding(.vertical, 6)
                }
            }
        }
    }

    private func exportCard(_ review: Review) -> some View {
        StabilisCard {
            VStack(alignment: .leading, spacing: 10) {
                Text("Share review").font(.headline).accessibilityAddTraits(.isHeader)
                if !store.isDemo {
                    Text("The access link opens for teammates with a matching workspace grant. Only share the written summary with authorized recipients.")
                        .font(.subheadline).foregroundStyle(StabilisStyle.secondary)
                    ShareLink(item: store.link(to: review)) { Label("Share access link", systemImage: "link") }
                        .buttonStyle(StabilisButtonStyle(primary: false))
                }
                ShareLink(item: PrintableReview(text: review.shareText(location: store.locationName, demo: store.isDemo)),
                          preview: SharePreview("Stabilis weekly labor review", image: Image(systemName: "doc.text"))) {
                    Label("Share review summary", systemImage: "square.and.arrow.up")
                }
                .buttonStyle(StabilisButtonStyle(primary: false))
                .accessibilityIdentifier("review.shareSummary")
            }
        }
    }
}

struct ReviewRow: View {
    let label: String
    let value: String

    var body: some View {
        ViewThatFits(in: .horizontal) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(verbatim: label).fixedSize()
                Spacer(minLength: 0)
                Text(verbatim: value).fontWeight(.semibold).multilineTextAlignment(.trailing).fixedSize()
            }
            VStack(alignment: .leading, spacing: 3) {
                Text(verbatim: label)
                Text(verbatim: value).fontWeight(.semibold).fixedSize(horizontal: false, vertical: true)
            }
        }
        .font(.subheadline)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(verbatim: label))
        .accessibilityValue(Text(verbatim: value))
    }
}
