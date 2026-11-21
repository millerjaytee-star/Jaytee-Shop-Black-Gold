import Foundation
import SwiftUI

enum WorkspaceMode: Equatable {
    case welcome, demo, customer
}

enum DemoRole: String, CaseIterable, Identifiable {
    case owner = "OWNER_EXECUTIVE"
    case manager = "GENERAL_MANAGER"

    var id: String { rawValue }
    var label: String { self == .owner ? "Owner" : "General manager" }
}

@MainActor
final class WorkspaceStore: ObservableObject {
    @Published private(set) var mode = WorkspaceMode.welcome
    @Published private(set) var organizations: [Scope] = []
    @Published private(set) var locations: [Scope] = []
    @Published private(set) var organizationID: UUID?
    @Published private(set) var locationID: UUID?
    @Published private(set) var reviews: [Review] = []
    @Published private(set) var assignees: [Assignee] = []
    @Published private(set) var demoRole = DemoRole.owner
    @Published private(set) var userID: UUID?
    @Published private(set) var busy = false
    @Published private(set) var saving = false
    @Published private(set) var error: String?
    @Published private(set) var notice: String?
    @Published var requestedReview: UUID?

    let webOrigin: URL
    let supportOrigin: URL
    let serviceName: String
    let recoveryURL: URL?
    private let client: WorkspaceClient?
    private let demo = FictionalWorkspace()
    private var availableLocations: [Scope] = []
    @Published private var pending: ReviewLink?
    private var revision = UUID()
    private var restored = false

    init(client: WorkspaceClient?, webOrigin: URL, serviceName: String,
         recoveryURL: URL? = nil, supportOrigin: URL? = nil) {
        self.client = client
        self.webOrigin = webOrigin
        self.supportOrigin = supportOrigin ?? webOrigin
        self.serviceName = serviceName
        self.recoveryURL = recoveryURL
    }

    var canSignIn: Bool { client != nil }
    var isDemo: Bool { mode == .demo }
    var role: String {
        if isDemo { return demoRole.rawValue }
        return locations.first { $0.id == locationID }?.role
            ?? organizations.first { $0.id == organizationID }?.role ?? "READ_ONLY"
    }
    var locationName: String {
        if isDemo { return "Juniper Café" }
        return locations.first { $0.id == locationID }?.name ?? "Select a location"
    }
    var needsSignInForLink: Bool { mode == .welcome && pending != nil }
    var canAssign: Bool { ["OWNER_EXECUTIVE", "AREA_MANAGER"].contains(role) }
    var canReviewEvidence: Bool { canAssign || ["STABILIS_ADMIN", "STABILIS_ANALYST"].contains(role) }

    func isAssignedManager(_ review: Review) -> Bool {
        role == "GENERAL_MANAGER" && userID != nil &&
        review.action?["assignee_id"]?.labelText.flatMap(UUID.init(uuidString:)) == userID
    }

    func restore() async {
        guard !restored, let client else { return }
        restored = true
        let stamp = beginRead()
        defer { finishRead(stamp) }
        do {
            if try await client.restore(), revision == stamp, mode == .welcome {
                mode = .customer
                try await loadWorkspace(stamp)
            }
        } catch { show(error, stamp: stamp) }
    }

    func signIn(email: String, password: String) async -> Bool {
        guard let client, mode == .welcome, !busy else { return false }
        let stamp = beginRead()
        defer { finishRead(stamp) }
        do {
            try await client.signIn(email: email.trimmingCharacters(in: .whitespacesAndNewlines), password: password)
            guard revision == stamp else { return false }
            mode = .customer
            try await loadWorkspace(stamp)
            return true
        } catch {
            show(error, stamp: stamp)
            return mode == .customer
        }
    }

    func sendRecovery(email: String) async -> Bool {
        guard let client, let recoveryURL, !busy else { return false }
        let stamp = beginRead()
        defer { finishRead(stamp) }
        do {
            try await client.requestRecovery(email: email.trimmingCharacters(in: .whitespacesAndNewlines), redirectTo: recoveryURL)
            guard revision == stamp else { return false }
            notice = "If this address belongs to a client account, check your inbox for the recovery link. Return here to sign in with your new password."
            return true
        } catch {
            show(error, stamp: stamp)
            return false
        }
    }

    func startDemo() {
        guard mode == .welcome else { return }
        revision = UUID()
        busy = false
        mode = .demo
        demoRole = .owner
        userID = FictionalWorkspace.managerID
        assignees = [Assignee(id: FictionalWorkspace.managerID, name: "Morgan Ellis")]
        reviews = [demo.review]
        error = nil
        notice = nil
    }

    func setDemoRole(_ role: DemoRole) {
        if isDemo { demoRole = role }
    }

    func resetDemo() {
        guard isDemo, !saving else { return }
        demo.reset()
        demoRole = .owner
        reviews = [demo.review]
        notice = "Fictional review reset."
        error = nil
    }

    func leave() async {
        guard !saving else { return }
        let wasCustomer = mode == .customer
        let stamp = beginRead()
        mode = .welcome
        clearWorkspace()
        defer { finishRead(stamp) }
        if wasCustomer {
            do { try await client?.signOut() }
            catch { show(error, stamp: stamp) }
        }
    }

    func refresh() async {
        guard mode == .customer, !busy, !saving else { return }
        let stamp = beginRead()
        defer { finishRead(stamp) }
        do { try await loadWorkspace(stamp) }
        catch { show(error, stamp: stamp) }
    }

    func selectOrganization(_ id: UUID) async {
        guard organizations.contains(where: { $0.id == id }), !saving else { return }
        let stamp = beginRead()
        defer { finishRead(stamp) }
        organizationID = id
        locations = availableLocations.filter { $0.organizationId == id }
        do { try await loadLocation(locations.first?.id, stamp: stamp) }
        catch { show(error, stamp: stamp) }
    }

    func selectLocation(_ id: UUID) async {
        guard locations.contains(where: { $0.id == id }), !saving else { return }
        let stamp = beginRead()
        defer { finishRead(stamp) }
        do { try await loadLocation(id, stamp: stamp) }
        catch { show(error, stamp: stamp) }
    }

    func handleLink(_ url: URL) async {
        guard let link = ReviewLink(url: url, webOrigin: webOrigin) else { return }
        pending = link
        if mode == .demo, !saving { await leave() }
        if mode == .customer, !saving {
            let stamp = beginRead()
            defer { finishRead(stamp) }
            do { try await loadWorkspace(stamp) }
            catch { show(error, stamp: stamp) }
        }
    }

    func link(to review: Review) -> URL {
        ReviewLink(organization: review.organizationId, location: review.locationId, review: review.id).url(origin: webOrigin)
    }

    func rememberReview(_ id: UUID) {
        guard mode == .customer, let userID, let review = reviews.first(where: { $0.id == id }) else { return }
        UserDefaults.standard.set(link(to: review).absoluteString, forKey: resumeKey(userID))
    }

    func save(_ review: Review, operation: String, payload: [String: JSONValue] = [:]) async -> Bool {
        guard mode != .welcome, !busy, !saving, reviews.contains(where: { $0.id == review.id && $0.version == review.version }) else { return false }
        saving = true
        error = nil
        notice = nil
        defer {
            saving = false
            if pending != nil, mode == .customer { Task { await refresh() } }
        }
        do {
            let saved: Review
            if isDemo {
                saved = try demo.save(review, role: demoRole, operation: operation, payload: payload)
            } else if let client {
                saved = try await client.save(review, operation: operation, payload: payload)
            } else {
                return false
            }
            if let index = reviews.firstIndex(where: { $0.id == saved.id }) { reviews[index] = saved }
            notice = ["assign": "Action assigned.", "accept": "Action accepted.", "request_change": "Change request sent.", "submit_evidence": "Evidence submitted.", "compare": "Weekly comparison saved.", "clarify": "Clarification requested.", "reopen": "Action reopened."][operation] ?? "Review updated."
            return true
        } catch {
            show(error, stamp: revision)
            return false
        }
    }

    private func beginRead() -> UUID {
        revision = UUID()
        busy = true
        error = nil
        notice = nil
        return revision
    }

    private func finishRead(_ stamp: UUID) {
        if revision == stamp { busy = false }
    }

    private func show(_ failure: Error, stamp: UUID) {
        guard revision == stamp else { return }
        if let issue = failure as? WorkspaceError {
            switch issue {
            case .signedOut:
                mode = .welcome
                clearWorkspace()
            case .access:
                reviews = []
                assignees = []
                requestedReview = nil
            default: break
            }
        }
        error = failure.localizedDescription
    }

    private func clearWorkspace() {
        organizations = []
        availableLocations = []
        locations = []
        organizationID = nil
        locationID = nil
        reviews = []
        assignees = []
        requestedReview = nil
        userID = nil
    }

    private func resumeKey(_ id: UUID) -> String {
        "stabilis-ios-last-review-\(serviceName)-\(webOrigin.host ?? "workspace")-\(id.uuidString)"
    }

    private func loadWorkspace(_ stamp: UUID) async throws {
        guard let client else { return }
        let user = await client.userID()
        let orgs = try await client.organizations()
        let allLocations = try await client.locations()
        guard revision == stamp, mode == .customer else { return }
        userID = user
        organizations = orgs
        availableLocations = allLocations
        let incoming = pending
        let remembered: ReviewLink?
        if organizationID == nil, let user, let saved = UserDefaults.standard.string(forKey: resumeKey(user)), let url = URL(string: saved) {
            remembered = ReviewLink(url: url, webOrigin: webOrigin)
        } else {
            remembered = nil
        }
        let link = incoming ?? remembered
        if let link, orgs.contains(where: { $0.id == link.organization }),
           allLocations.contains(where: { $0.id == link.location && $0.organizationId == link.organization }) {
            organizationID = link.organization
            locations = allLocations.filter { $0.organizationId == link.organization }
            try await loadLocation(link.location, stamp: stamp)
            guard revision == stamp else { return }
            pending = nil
            if reviews.contains(where: { $0.id == link.review }) { requestedReview = link.review }
            else if incoming != nil { error = "This review is unavailable. Check your access with your workspace administrator." }
        } else {
            let selected = orgs.first(where: { $0.id == organizationID })?.id ?? orgs.first?.id
            organizationID = selected
            locations = allLocations.filter { $0.organizationId == selected }
            try await loadLocation(locations.first(where: { $0.id == locationID })?.id ?? locations.first?.id, stamp: stamp)
            if incoming != nil, revision == stamp {
                pending = nil
                error = "This review is unavailable. Check your access with your workspace administrator."
            }
        }
    }

    private func loadLocation(_ id: UUID?, stamp: UUID) async throws {
        if locationID != id {
            reviews = []
            assignees = []
            requestedReview = nil
        }
        locationID = id
        guard let client, let org = organizationID, let id else { return }
        let records = try await client.reviews(org: org, location: id)
        guard revision == stamp, mode == .customer else { return }
        reviews = records
        if canAssign {
            let roster = try await client.assignees(org: org, location: id)
            if revision == stamp, mode == .customer { assignees = roster }
        } else {
            assignees = []
        }
    }
}

extension JSONValue {
    var labelText: String? { if case let .string(value) = self { return value }; return nil }
    var finiteNumber: Double? { if case let .number(value) = self, value.isFinite { return value }; return nil }
    var fields: [String: JSONValue]? { if case let .object(value) = self { return value }; return nil }
    var flag: Bool? { if case let .bool(value) = self { return value }; return nil }
}
