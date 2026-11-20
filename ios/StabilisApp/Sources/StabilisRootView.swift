import SwiftUI

struct StabilisRootView: View {
    @ObservedObject var store: WorkspaceStore
    @Environment(\.scenePhase) private var scenePhase
    @State private var path: [UUID] = []
    @State private var showSignIn = false
    @State private var showReset = false

    var body: some View {
        NavigationStack(path: $path) {
            Group {
                if store.mode == .welcome { welcome }
                else { workspace }
            }
            .navigationDestination(for: UUID.self) { id in
                ReviewDetailView(id: id, store: store)
            }
        }
        .tint(StabilisStyle.accent)
        .onOpenURL { url in Task { await store.handleLink(url) } }
        .onContinueUserActivity("NSUserActivityTypeBrowsingWeb") { activity in
            guard let url = activity.webpageURL else { return }
            Task { await store.handleLink(url) }
        }
        .task { await store.restore() }
        .onChange(of: store.requestedReview) { _, id in
            if let id {
                path = [id]
                store.requestedReview = nil
            }
        }
        .onChange(of: path) { _, current in
            if let id = current.last { store.rememberReview(id) }
        }
        .onChange(of: store.mode) { _, mode in
            if mode == .welcome { path = [] }
        }
        .onChange(of: scenePhase) { previous, current in
            if previous != .active && current == .active { Task { await store.refresh() } }
        }
        .sheet(isPresented: $showSignIn) { SignInView(store: store) }
        .overlay {
            if store.mode == .customer && scenePhase != .active {
                StabilisStyle.paper.ignoresSafeArea().overlay { StabilisMark() }
                    .accessibilityHidden(true)
            }
        }
    }

    private var welcome: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                HStack(spacing: 12) {
                    StabilisMark()
                    Text("Stabilis Operator Intelligence™").font(.headline)
                }
                VStack(alignment: .leading, spacing: 10) {
                    Text("Know why labor missed plan.")
                        .font(.system(.largeTitle, design: .serif).weight(.semibold))
                        .accessibilityAddTraits(.isHeader)
                    Text("Review the schedule, sales and payroll. Give the next step to a manager and see what changes the following week.")
                        .foregroundStyle(StabilisStyle.secondary)
                }
                StabilisCard {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Juniper Café had a $450 labor overage.")
                            .font(.headline)
                            .accessibilityAddTraits(.isHeader)
                        Text("Try the owner and general manager steps with fictional records saved on this device.")
                            .font(.subheadline).foregroundStyle(StabilisStyle.secondary)
                        Button("Try fictional review") { store.startDemo() }
                            .buttonStyle(StabilisButtonStyle())
                            .accessibilityIdentifier("demo.open")
                    }
                }
                VStack(alignment: .leading, spacing: 9) {
                    Button(store.needsSignInForLink ? "Sign in to open review" : "Client sign in") { showSignIn = true }
                        .buttonStyle(StabilisButtonStyle(primary: false))
                        .disabled(store.busy || !store.canSignIn)
                        .accessibilityIdentifier("signin.open")
                    if !store.canSignIn {
                        WorkspaceMessage(text: "This build has no client workspace connection. The fictional review is available.")
                    } else if store.needsSignInForLink {
                        WorkspaceMessage(text: "A workspace invitation and location access are required to open this review.")
                    }
                    if store.busy { ProgressView("Checking your workspace…") }
                    if let error = store.error { WorkspaceMessage(text: error, isError: true) }
                }
                supportLinks
            }
            .frame(maxWidth: 560)
            .padding(20)
            .frame(maxWidth: .infinity)
        }
        .foregroundStyle(StabilisStyle.ink)
        .background(StabilisStyle.paper.ignoresSafeArea())
        .toolbar(.hidden, for: .navigationBar)
    }

    private var workspace: some View {
        List {
            if store.isDemo {
                Section {
                    Label("Fictional data · Juniper Café", systemImage: "cup.and.saucer")
                    Picker("Your role", selection: Binding(get: { store.demoRole }, set: { store.setDemoRole($0) })) {
                        ForEach(DemoRole.allCases) { role in Text(role.label).tag(role) }
                    }
                    .accessibilityIdentifier("demo.role")
                } footer: {
                    Text("Practice the owner and manager steps. This review stays on this device.")
                }
                .listRowBackground(StabilisStyle.card)
            } else {
                customerSelection
            }

            if let error = store.error {
                WorkspaceMessage(text: error, isError: true).listRowBackground(StabilisStyle.card)
                if !store.isDemo {
                    Button("Reload workspace") { Task { await store.refresh() } }
                        .disabled(store.busy || store.saving)
                        .listRowBackground(StabilisStyle.card)
                }
            }
            if let notice = store.notice { WorkspaceMessage(text: notice).listRowBackground(StabilisStyle.card) }
            if store.busy { ProgressView("Loading weekly reviews…").listRowBackground(StabilisStyle.card) }

            Section {
                if store.reviews.isEmpty, !store.busy {
                    Text(store.locationID == nil ? "Your organization and location grants will appear after sign-in." : "Released labor reviews for this location will appear here.")
                        .foregroundStyle(StabilisStyle.secondary)
                }
                ForEach(store.reviews) { review in
                    NavigationLink(value: review.id) {
                        VStack(alignment: .leading, spacing: 5) {
                            Text("Week of \(WeekDate.display(review.weekStart))").font(.headline)
                            Text(review.statusLabel).font(.subheadline).foregroundStyle(StabilisStyle.secondary)
                        }
                        .padding(.vertical, 6)
                        .accessibilityElement(children: .combine)
                    }
                    .accessibilityIdentifier(store.isDemo ? "demo.review" : "customer.review")
                }
            } header: {
                Text("Weekly labor reviews")
            }
            .listRowBackground(StabilisStyle.card)

            Section {
                supportLinks
                if store.isDemo {
                    Button("Reset fictional review", role: .destructive) { showReset = true }
                        .disabled(store.saving)
                        .accessibilityIdentifier("demo.reset")
                }
                Button(store.isDemo ? "Leave fictional review" : "Sign out") {
                    Task { await store.leave() }
                }
                .disabled(store.saving)
            }
            .listRowBackground(StabilisStyle.card)
        }
        .scrollContentBackground(.hidden)
        .background(StabilisStyle.paper.ignoresSafeArea())
        .foregroundStyle(StabilisStyle.ink)
        .navigationTitle(store.isDemo ? "Fictional workspace" : "Weekly labor")
        .refreshable { await store.refresh() }
        .confirmationDialog("Reset the fictional review?", isPresented: $showReset, titleVisibility: .visible) {
            Button("Reset fictional review", role: .destructive) { store.resetDemo() }
                .accessibilityIdentifier("demo.confirmReset")
            Button("Cancel", role: .cancel) { }
        } message: {
            Text("Your practice assignment, evidence and comparison will be cleared from this device.")
        }
    }

    private var customerSelection: some View {
        Section {
            if store.organizations.count > 1 {
                Picker("Organization", selection: Binding(get: { store.organizationID }, set: { id in
                    if let id { Task { await store.selectOrganization(id) } }
                })) {
                    ForEach(store.organizations) { org in Text(org.name).tag(Optional(org.id)) }
                }
                .disabled(store.busy || store.saving)
            } else if let organization = store.organizations.first {
                LabeledContent("Organization", value: organization.name)
            }
            if !store.locations.isEmpty {
                Picker("Location", selection: Binding(get: { store.locationID }, set: { id in
                    if let id { Task { await store.selectLocation(id) } }
                })) {
                    ForEach(store.locations) { location in Text(location.name).tag(Optional(location.id)) }
                }
                .disabled(store.busy || store.saving)
            }
            if !store.organizations.isEmpty { LabeledContent("Role", value: store.role.displayRole) }
        } header: {
            Text(store.serviceName)
        }
        .listRowBackground(StabilisStyle.card)
    }

    private var supportLinks: some View {
        VStack(alignment: .leading, spacing: 2) {
            Link("Support and accessibility", destination: store.webOrigin.appendingPathComponent("support"))
            Link("Privacy policy", destination: store.webOrigin.appendingPathComponent("privacy"))
            if let deletion = accountDeletionURL {
                Link("Request account deletion", destination: deletion)
            }
        }
        .font(.subheadline.weight(.medium))
        .buttonStyle(.plain)
        .foregroundStyle(StabilisStyle.accent)
        .lineSpacing(4)
    }

    private var accountDeletionURL: URL? {
        var components = URLComponents(url: store.webOrigin.appendingPathComponent("support"), resolvingAgainstBaseURL: false)
        components?.fragment = "account-deletion"
        return components?.url
    }
}

private struct SignInView: View {
    @ObservedObject var store: WorkspaceStore
    @Environment(\.dismiss) private var dismiss
    @State private var email = ""
    @State private var password = ""
    @State private var recovery = false
    @FocusState private var focus: Field?

    private enum Field { case email, password }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Work email", text: $email)
                        .keyboardType(.emailAddress)
                        .textContentType(.username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .focused($focus, equals: .email)
                        .submitLabel(recovery ? .go : .next)
                        .onSubmit { if recovery { submit() } else { focus = .password } }
                    if !recovery {
                        SecureField("Password", text: $password)
                            .textContentType(.password)
                            .focused($focus, equals: .password)
                            .submitLabel(.go)
                            .onSubmit { submit() }
                    }
                } footer: {
                    Text(recovery ? "Use the email address associated with your invitation." : "Client access is by invitation from your Stabilis workspace administrator.")
                }
                Section {
                    Button(recovery ? "Send recovery link" : "Sign in") { submit() }
                        .disabled(disabled)
                    if store.busy { ProgressView(recovery ? "Sending link…" : "Signing in…") }
                    if let error = store.error { WorkspaceMessage(text: error, isError: true) }
                    if let notice = store.notice { WorkspaceMessage(text: notice) }
                    if store.recoveryURL != nil {
                        Button(recovery ? "Back to sign in" : "Reset password") {
                            recovery.toggle()
                            password = ""
                            focus = .email
                        }
                        .disabled(store.busy)
                    } else {
                        Link("Get sign-in help", destination: store.webOrigin.appendingPathComponent("support"))
                    }
                }
            }
            .navigationTitle(recovery ? "Password recovery" : "Client sign in")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }.disabled(store.busy)
                }
            }
            .interactiveDismissDisabled(store.busy)
            .onDisappear { password = "" }
        }
    }

    private var disabled: Bool {
        let address = email.trimmingCharacters(in: .whitespacesAndNewlines)
        return store.busy || !address.contains("@") || (!recovery && password.isEmpty)
    }

    private func submit() {
        guard !disabled else { return }
        focus = nil
        if recovery {
            Task { _ = await store.sendRecovery(email: email) }
        } else {
            Task {
                if await store.signIn(email: email, password: password) { dismiss() }
                password = ""
            }
        }
    }
}

extension String {
    var displayRole: String {
        ["OWNER_EXECUTIVE": "Owner", "AREA_MANAGER": "Area manager", "GENERAL_MANAGER": "General manager", "READ_ONLY": "Read-only", "STABILIS_ADMIN": "Stabilis administrator", "STABILIS_ANALYST": "Stabilis analyst"][self] ?? "Workspace member"
    }
}
