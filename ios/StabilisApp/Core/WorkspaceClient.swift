import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
#if canImport(Security)
import Security
#endif

enum JSONValue: Codable, Equatable, Sendable {
    case string(String), number(Double), bool(Bool), object([String: JSONValue]), array([JSONValue]), null

    init(from decoder: Decoder) throws {
        let value = try decoder.singleValueContainer()
        if value.decodeNil() { self = .null }
        else if let item = try? value.decode(Bool.self) { self = .bool(item) }
        else if let item = try? value.decode(Double.self) { self = .number(item) }
        else if let item = try? value.decode(String.self) { self = .string(item) }
        else if let item = try? value.decode([String: JSONValue].self) { self = .object(item) }
        else { self = .array(try value.decode([JSONValue].self)) }
    }

    func encode(to encoder: Encoder) throws {
        var value = encoder.singleValueContainer()
        switch self {
        case .string(let item): try value.encode(item)
        case .number(let item): try value.encode(item)
        case .bool(let item): try value.encode(item)
        case .object(let item): try value.encode(item)
        case .array(let item): try value.encode(item)
        case .null: try value.encodeNil()
        }
    }
}

struct Review: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    let organizationId: UUID
    let locationId: UUID
    let weekStart: String
    var status: String
    var source: String
    var version: Int
    var inputs: [String: Double?]
    var metrics: [String: Double?]
    var action: [String: JSONValue]?
    var followup: [String: JSONValue]?
    var verification: [String: JSONValue]?
}

struct Scope: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    let name: String
    var code: String?
    var role: String?
    var organizationId: UUID?
}

struct Assignee: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    let name: String
}

enum WorkspaceError: LocalizedError, Equatable {
    case signedOut, credentials, access, stale, service, invalidResponse, secureStorage
    case rejected

    var errorDescription: String? {
        switch self {
        case .signedOut: return "Your session ended. Sign in to reopen this review."
        case .credentials: return "Check your work email and password, then try again."
        case .access: return "This record is unavailable for your workspace access."
        case .stale: return "The review changed. Refresh it before trying again."
        case .service: return "The workspace could not be reached. Check your connection and try again."
        case .invalidResponse: return "The workspace returned an unexpected response. Try again shortly."
        case .secureStorage: return "Secure session storage is unavailable. Unlock your device and try again."
        case .rejected: return "The workspace could not save this update. Review the details and current status."
        }
    }
}

private struct Credentials: Decodable, Sendable {
    struct Account: Decodable, Sendable { let id: UUID }
    let accessToken: String
    let refreshToken: String
    let expiresIn: Double
    let user: Account?
}

actor WorkspaceClient {
    private let baseURL: URL
    private let key: String
    private let network: URLSession
    private let vault: RefreshTokenVault
    private var credentials: Credentials?
    private var expiresAt = Date.distantPast
    private var accountID: UUID?
    private var generation = 0
    private var renewal: (id: UUID, task: Task<Credentials, Error>)?

    init(baseURL: URL, key: String, network: URLSession? = nil, rememberSession: Bool = true) {
        self.baseURL = baseURL
        self.key = key
        self.vault = RefreshTokenVault(account: baseURL.absoluteString, enabled: rememberSession)
        let config = URLSessionConfiguration.ephemeral
        config.urlCache = nil
        config.httpCookieStorage = nil
        config.timeoutIntervalForRequest = 20
        self.network = network ?? URLSession(configuration: config, delegate: NoRedirects(), delegateQueue: nil)
    }

    func userID() -> UUID? { accountID }

    func restore() async throws -> Bool {
        guard try vault.read() != nil || credentials != nil else { return false }
        do {
            let session = try await currentCredentials()
            try await resolveAccount(session)
            return true
        } catch WorkspaceError.signedOut {
            return false
        }
    }

    func signIn(email: String, password: String) async throws {
        try clear()
        let operation = generation
        let next: Credentials
        do {
            next = try await send(
                "/auth/v1/token", query: [URLQueryItem(name: "grant_type", value: "password")],
                payload: ["email": .string(email), "password": .string(password)]
            )
        } catch WorkspaceError.signedOut {
            throw WorkspaceError.credentials
        }
        guard generation == operation else { throw WorkspaceError.signedOut }
        try store(next)
        try await resolveAccount(next)
    }

    func signOut() async throws {
        let previous = credentials
        try clear()
        if let previous {
            // Scope revocation to this session. Local sign-out takes effect before network I/O.
            let _: Empty = try await send(
                "/auth/v1/logout", query: [URLQueryItem(name: "scope", value: "local")],
                payload: [:], bearer: previous.accessToken
            )
        }
    }

    func requestRecovery(email: String, redirectTo: URL) async throws {
        let _: Empty = try await send(
            "/auth/v1/recover", query: [URLQueryItem(name: "redirect_to", value: redirectTo.absoluteString)],
            payload: ["email": .string(email)]
        )
    }

    func organizations() async throws -> [Scope] {
        try await authorized("/rest/v1/stabilis_my_organizations")
    }

    func locations() async throws -> [Scope] {
        try await authorized("/rest/v1/stabilis_my_locations")
    }

    func reviews(org: UUID, location: UUID) async throws -> [Review] {
        try await authorized("/rest/v1/rpc/stabilis_labor_reviews", payload: scope(org, location))
    }

    func assignees(org: UUID, location: UUID) async throws -> [Assignee] {
        try await authorized("/rest/v1/rpc/stabilis_labor_assignees", payload: scope(org, location))
    }

    func save(_ review: Review, operation: String, payload: [String: JSONValue]) async throws -> Review {
        var request = scope(review.organizationId, review.locationId)
        request["p_review_id"] = .string(review.id.uuidString)
        request["p_version"] = .number(Double(review.version))
        request["p_operation"] = .string(operation)
        request["p_payload"] = .object(payload)
        return try await authorized("/rest/v1/rpc/stabilis_save_labor_review", payload: request)
    }

    private func scope(_ org: UUID, _ location: UUID) -> [String: JSONValue] {
        ["p_organization_id": .string(org.uuidString), "p_location_id": .string(location.uuidString)]
    }

    private func authorized<T: Decodable & Sendable>(_ endpoint: String, payload: [String: JSONValue]? = nil) async throws -> T {
        let operation = generation
        let first = try await currentCredentials()
        guard generation == operation else { throw WorkspaceError.signedOut }
        let result: T
        do {
            result = try await send(endpoint, payload: payload, bearer: first.accessToken)
        } catch WorkspaceError.signedOut {
            guard generation == operation else { throw WorkspaceError.signedOut }
            let next = try await currentCredentials(expiredToken: first.accessToken)
            guard generation == operation else { throw WorkspaceError.signedOut }
            result = try await send(endpoint, payload: payload, bearer: next.accessToken)
        }
        guard generation == operation else { throw WorkspaceError.signedOut }
        return result
    }

    private func currentCredentials(expiredToken: String? = nil) async throws -> Credentials {
        if let credentials, expiresAt > Date(), credentials.accessToken != expiredToken { return credentials }
        let operation = generation
        let pending: (id: UUID, task: Task<Credentials, Error>)
        if let renewal {
            pending = renewal
        } else {
            guard let token = try credentials?.refreshToken ?? vault.read() else { throw WorkspaceError.signedOut }
            pending = (UUID(), Task {
                try await send(
                    "/auth/v1/token", query: [URLQueryItem(name: "grant_type", value: "refresh_token")],
                    payload: ["refresh_token": .string(token)]
                )
            })
            renewal = pending
        }
        do {
            let next = try await pending.task.value
            guard generation == operation else { throw WorkspaceError.signedOut }
            if renewal?.id == pending.id {
                renewal = nil
                try store(next)
            }
            guard let credentials else { throw WorkspaceError.signedOut }
            return credentials
        } catch {
            if renewal?.id == pending.id {
                renewal = nil
                if error as? WorkspaceError == .signedOut || error as? WorkspaceError == .rejected {
                    try clear()
                    throw WorkspaceError.signedOut
                }
            }
            throw error
        }
    }

    private func resolveAccount(_ session: Credentials) async throws {
        if accountID != nil { return }
        let operation = generation
        let identity: Credentials.Account = try await send("/auth/v1/user", bearer: session.accessToken)
        guard generation == operation else { throw WorkspaceError.signedOut }
        accountID = identity.id
    }

    private func store(_ next: Credentials) throws {
        try vault.write(next.refreshToken)
        credentials = next
        expiresAt = Date().addingTimeInterval(max(0, next.expiresIn - 30))
        accountID = next.user?.id ?? accountID
    }

    private func clear() throws {
        generation += 1
        renewal?.task.cancel()
        renewal = nil
        credentials = nil
        expiresAt = .distantPast
        accountID = nil
        try vault.remove()
    }

    private struct Empty: Decodable, Sendable {}
    private struct ServerError: Decodable { let code: String? }

    private func send<T: Decodable & Sendable>(
        _ path: String, query: [URLQueryItem] = [], payload: [String: JSONValue]? = nil, bearer: String? = nil
    ) async throws -> T {
        guard var address = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) else {
            throw WorkspaceError.service
        }
        address.path = path
        address.queryItems = query.isEmpty ? nil : query
        guard let url = address.url else { throw WorkspaceError.service }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData)
        request.setValue(key, forHTTPHeaderField: "apikey")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let bearer { request.setValue("Bearer \(bearer)", forHTTPHeaderField: "Authorization") }
        if let payload {
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(payload)
        }
        let (data, response): (Data, URLResponse)
        do { (data, response) = try await network.data(for: request) }
        catch is CancellationError { throw CancellationError() }
        catch { throw WorkspaceError.service }
        guard let http = response as? HTTPURLResponse else { throw WorkspaceError.invalidResponse }
        switch http.statusCode {
        case 200...299: break
        case 401: throw WorkspaceError.signedOut
        case 403, 404: throw WorkspaceError.access
        case 409: throw WorkspaceError.stale
        case 429, 500...599: throw WorkspaceError.service
        default:
            let body = try? JSONDecoder().decode(ServerError.self, from: data)
            if body?.code == "40001" { throw WorkspaceError.stale }
            if path.hasPrefix("/auth/v1/token") { throw WorkspaceError.signedOut }
            throw WorkspaceError.rejected
        }
        if T.self == Empty.self, let empty = Empty() as? T { return empty }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        do { return try decoder.decode(T.self, from: data) }
        catch { throw WorkspaceError.invalidResponse }
    }
}

private final class NoRedirects: NSObject, URLSessionTaskDelegate, Sendable {
    func urlSession(
        _ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
        newRequest request: URLRequest, completionHandler: @escaping @Sendable (URLRequest?) -> Void
    ) {
        completionHandler(nil)
    }
}

private struct RefreshTokenVault: Sendable {
    let account: String
    let enabled: Bool

    #if canImport(Security)
    private var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: "com.stabilisops.operatorintelligence.session",
         kSecAttrAccount as String: account]
    }
    #endif

    func read() throws -> String? {
        #if canImport(Security)
        guard enabled else { return nil }
        var request = query
        request[kSecReturnData as String] = true
        request[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        let status = SecItemCopyMatching(request as CFDictionary, &item)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = item as? Data,
              let value = String(data: data, encoding: .utf8) else { throw WorkspaceError.secureStorage }
        return value
        #else
        return nil
        #endif
    }

    func write(_ value: String) throws {
        #if canImport(Security)
        guard enabled else { return }
        let data = Data(value.utf8)
        let status = SecItemUpdate(query as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if status == errSecItemNotFound {
            var item = query
            item[kSecValueData as String] = data
            item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { throw WorkspaceError.secureStorage }
        } else if status != errSecSuccess {
            throw WorkspaceError.secureStorage
        }
        #endif
    }

    func remove() throws {
        #if canImport(Security)
        guard enabled else { return }
        let status = SecItemDelete(query as CFDictionary)
        if status != errSecSuccess && status != errSecItemNotFound { throw WorkspaceError.secureStorage }
        #endif
    }
}
