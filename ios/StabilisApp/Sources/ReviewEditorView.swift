import SwiftUI

enum ReviewEditor: String, Identifiable {
    case assign, change = "request_change", evidence = "submit_evidence", compare, clarify, reopen

    var id: String { rawValue }

    var title: String {
        switch self {
        case .assign: return "Approve assignment"
        case .change: return "Request a change"
        case .evidence: return "Record evidence"
        case .compare: return "Compare weeks"
        case .clarify: return "Request clarification"
        case .reopen: return "Reopen action"
        }
    }

    var saveLabel: String {
        switch self {
        case .assign: return "Assign"
        case .change, .clarify: return "Send"
        case .evidence: return "Submit"
        case .compare: return "Save"
        case .reopen: return "Reopen"
        }
    }

    var saveIdentifier: String {
        switch self {
        case .assign: return "review.saveAssignment"
        case .evidence: return "review.submitEvidence"
        case .compare: return "review.saveComparison"
        default: return "review.send.\(rawValue)"
        }
    }
}

struct ReviewEditorView: View {
    @ObservedObject var store: WorkspaceStore
    let review: Review
    let editor: ReviewEditor
    @Environment(\.dismiss) private var dismiss

    @State private var manager: UUID?
    @State private var decision: String
    @State private var target: String
    @State private var evidenceRequired: String
    @State private var due: Date
    @State private var nextReview: Date
    @State private var comparisonWeek: Date
    @State private var inputs: [String: String]
    @State private var source: String
    @State private var comparable = ""
    @State private var note: String
    @State private var validation: String?

    init(store: WorkspaceStore, review: Review, editor: ReviewEditor) {
        self.store = store
        self.review = review
        self.editor = editor
        _manager = State(initialValue: review.actionText("assignee_id").flatMap(UUID.init(uuidString:)) ?? store.assignees.first?.id)
        _decision = State(initialValue: review.actionText("title") ?? (store.isDemo ? "Check closing coverage against the schedule" : ""))
        _target = State(initialValue: review.actionText("target_measure") ?? (store.isDemo ? "Keep paid labor within 125 scheduled hours." : ""))
        _evidenceRequired = State(initialValue: review.actionText("evidence_required") ?? (store.isDemo ? "Record scheduled and paid closing hours for each day." : ""))
        _due = State(initialValue: review.actionText("due_date").flatMap(WeekDate.date) ?? WeekDate.adding(10, to: review.weekStart))
        _nextReview = State(initialValue: review.actionText("next_review").flatMap(WeekDate.date) ?? WeekDate.adding(14, to: review.weekStart))
        _comparisonWeek = State(initialValue: WeekDate.adding(7, to: review.weekStart))
        _inputs = State(initialValue: store.isDemo ? FictionalWorkspace.followingWeek.compactMapValues { value in
            value?.formatted(.number.grouping(.never).precision(.fractionLength(0...2)))
        } : [:])
        _source = State(initialValue: store.isDemo ? "Fictional Juniper Café following-week sales, schedule and payroll exports" : "")
        let exampleNote: String
        if editor == .compare {
            exampleNote = "Same operating hours and wage rates across both fictional weeks."
        } else if editor == .evidence {
            exampleNote = "Compared the closing schedule against paid time records for all seven days."
        } else {
            exampleNote = ""
        }
        _note = State(initialValue: store.isDemo ? exampleNote : "")
    }

    var body: some View {
        NavigationStack {
            Form {
                if let validation { WorkspaceMessage(text: validation, isError: true) }
                if let error = store.error { WorkspaceMessage(text: error, isError: true) }
                if store.saving { ProgressView("Saving…") }
                switch editor {
                case .assign: assignment
                case .compare: comparison
                case .evidence, .change, .clarify, .reopen: notes
                }
            }
            .scrollDismissesKeyboard(.interactively)
            .navigationTitle(editor.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }.disabled(store.saving)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(editor.saveLabel) { submit() }
                        .disabled(store.saving || store.busy)
                        .accessibilityIdentifier(editor.saveIdentifier)
                }
            }
            .interactiveDismissDisabled(store.saving)
        }
    }

    private var assignment: some View {
        Section {
            TextField("Corrective action", text: $decision, axis: .vertical)
            Picker("Responsible manager", selection: $manager) {
                Text("Choose a manager").tag(Optional<UUID>.none)
                ForEach(store.assignees) { assignee in Text(assignee.name).tag(Optional(assignee.id)) }
            }
            DatePicker("Due date", selection: $due, displayedComponents: .date)
            DatePicker("Next review", selection: $nextReview, displayedComponents: .date)
            TextField("Target measure", text: $target, axis: .vertical)
            TextField("Evidence to submit", text: $evidenceRequired, axis: .vertical)
        } footer: {
            Text("The assigned manager will see the decision, due date and requested evidence.")
        }
    }

    private var comparison: some View {
        Group {
            Section("Following week") {
                DatePicker("Fiscal week starts", selection: $comparisonWeek, displayedComponents: .date)
                Picker("Are the weeks comparable?", selection: $comparable) {
                    Text("Choose").tag("")
                    Text("Comparable").tag("yes")
                    Text("Incomparable").tag("no")
                }
                .accessibilityIdentifier("review.comparability")
                TextField("Source references", text: $source, axis: .vertical)
            }
            Section {
                ForEach(Review.fields, id: \.key) { field in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(field.name).font(.subheadline).foregroundStyle(StabilisStyle.secondary)
                        TextField("Enter value", text: Binding(get: { inputs[field.key] ?? "" }, set: { inputs[field.key] = $0 }))
                            .keyboardType(.decimalPad)
                            .accessibilityLabel(field.name)
                    }
                }
            } header: {
                Text("Forecast, schedule and actuals")
            } footer: {
                Text("Leave unrecorded figures empty. Enter 0 only when a report shows zero.")
            }
            Section("Conditions affecting the comparison") {
                noteField(label: "Sales, hours, holidays, rates or role mix")
            }
        }
    }

    private var notes: some View {
        Section {
            if editor == .evidence, let requested = review.actionText("evidence_required") {
                Text(verbatim: requested).font(.subheadline).foregroundStyle(StabilisStyle.secondary)
            }
            noteField(label: noteLabel)
        } header: {
            Text(noteLabel)
        } footer: {
            Text("Cite a report, shift record or observation the reviewer can check.")
        }
    }

    private func noteField(label: String) -> some View {
        TextEditor(text: $note)
            .frame(minHeight: 105)
            .accessibilityLabel(label)
            .accessibilityIdentifier(editor == .evidence ? "review.evidenceNote" : "review.note")
    }

    private var noteLabel: String {
        switch editor {
        case .evidence: return "Completion evidence"
        case .change: return "Requested change"
        case .clarify: return "What the GM needs to clarify"
        case .reopen: return "Reason for reopening"
        default: return "Review note"
        }
    }

    private func submit() {
        guard !store.saving, !store.busy else { return }
        do {
            let payload = try makePayload()
            validation = nil
            Task {
                if await store.save(review, operation: editor.rawValue, payload: payload) { dismiss() }
            }
        } catch {
            validation = error.localizedDescription
        }
    }

    private func makePayload() throws -> [String: JSONValue] {
        if editor == .assign {
            guard let manager, store.assignees.contains(where: { $0.id == manager }),
                  WeekDate.iso(due) >= review.weekStart, WeekDate.iso(nextReview) >= WeekDate.iso(due) else {
                throw ReviewInputError("Choose a manager and confirm the due date and next review.")
            }
            return ["title": try text(decision, name: "corrective action"), "assignee_id": .string(manager.uuidString),
                    "target_measure": try text(target, name: "target measure"), "evidence_required": try text(evidenceRequired, name: "evidence required"),
                    "due_date": .string(WeekDate.iso(due)), "next_review": .string(WeekDate.iso(nextReview))]
        }
        if editor == .compare {
            let calendar = Calendar(identifier: .gregorian)
            let start = WeekDate.date(review.weekStart) ?? comparisonWeek
            let days = calendar.dateComponents([.day], from: calendar.startOfDay(for: start), to: calendar.startOfDay(for: comparisonWeek)).day ?? 0
            guard days >= 7, days % 7 == 0, !comparable.isEmpty else {
                throw ReviewInputError("Choose a later week with the same fiscal starting day, then confirm comparability.")
            }
            return ["week_start": .string(WeekDate.iso(comparisonWeek)), "source": try text(source, name: "source references"),
                    "note": try text(note, name: "comparison note"), "comparable": .bool(comparable == "yes"), "inputs": .object(try numericInputs())]
        }
        return ["note": try text(note, name: noteLabel.lowercased())]
    }

    private func text(_ value: String, name: String) throws -> JSONValue {
        let value = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !value.isEmpty, value.count <= 1_000 else {
            throw ReviewInputError("Enter \(name) using 1 to 1,000 characters.")
        }
        return .string(value)
    }

    private func numericInputs() throws -> [String: JSONValue] {
        var mapped: [String: JSONValue] = [:]
        let locale = Locale.current
        for field in Review.fields {
            let value = inputs[field.key]?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if value.isEmpty { continue }
            let grouping = locale.groupingSeparator ?? ","
            let decimal = locale.decimalSeparator ?? "."
            let normalized = value.replacingOccurrences(of: grouping, with: "").replacingOccurrences(of: decimal, with: ".")
            let max = field.key == "target_pct" ? 100.0 : 1_000_000_000_000.0
            guard let number = Double(normalized), number.isFinite, (0...max).contains(number) else {
                throw ReviewInputError("Check the value for \(field.name.lowercased()).")
            }
            mapped[field.key] = .number(number)
        }
        if mapped.isEmpty { throw ReviewInputError("Enter at least one figure from the following week.") }
        return mapped
    }
}

private struct ReviewInputError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}
