import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import XCTest
@testable import WorkspaceCore

final class WorkspaceCoreTests: XCTestCase {
    func testLinksRoundTripAndRejectForeignOrCredentialBearingLinks() throws {
        let origin = try XCTUnwrap(URL(string: "https://stabilis-ops-group.netlify.app"))
        let expected = ReviewLink(organization: UUID(), location: UUID(), review: UUID())
        XCTAssertEqual(ReviewLink(url: expected.url(origin: origin), webOrigin: origin), expected)
        let ids = [expected.organization, expected.location, expected.review].map(\.uuidString).joined(separator: "/")
        XCTAssertEqual(ReviewLink(url: try XCTUnwrap(URL(string: "stabilis://review/\(ids)")), webOrigin: origin), expected)
        XCTAssertNil(ReviewLink(url: try XCTUnwrap(URL(string: "https://other.example/mobile/review/\(ids)")), webOrigin: origin))
        XCTAssertNil(ReviewLink(url: try XCTUnwrap(URL(string: "stabilis://review/\(ids)?access_token=fixture")), webOrigin: origin))
    }

    func testWireValuesPreserveBooleanNullDollarsAndNestedEvidence() throws {
        let raw = Data(#"{"comparable":false,"amount":150.25,"metrics":{"actual_pct":null},"evidence":"Closing checklist"}"#.utf8)
        let parsed = try JSONDecoder().decode(JSONValue.self, from: raw)
        XCTAssertEqual(parsed, .object([
            "comparable": .bool(false), "amount": .number(150.25),
            "metrics": .object(["actual_pct": .null]), "evidence": .string("Closing checklist")
        ]))
        XCTAssertEqual(try JSONDecoder().decode(JSONValue.self, from: JSONEncoder().encode(parsed)), parsed)
    }

    func testSignInFetchRefreshAndSignOut() async throws {
        let identity = UUID()
        let location = UUID()
        let org = UUID()
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [StubProtocol.self]
        let client = WorkspaceClient(baseURL: URL(string: "https://stabilis.example")!, key: "fixture",
                                     network: URLSession(configuration: config), rememberSession: false)
        StubProtocol.handler = { request in
            let url = try XCTUnwrap(request.url)
            let auth = request.value(forHTTPHeaderField: "Authorization")
            XCTAssertEqual(request.value(forHTTPHeaderField: "apikey"), "fixture")
            switch (url.path, url.query, auth) {
            case ("/auth/v1/token", "grant_type=password", nil):
                return (200, #"{"access_token":"first","refresh_token":"r1","expires_in":3600,"user":{"id":"\#(identity.uuidString)"}}"#)
            case ("/rest/v1/stabilis_my_locations", nil, "Bearer first"):
                return (401, "{}")
            case ("/auth/v1/token", "grant_type=refresh_token", nil):
                return (200, #"{"access_token":"second","refresh_token":"r2","expires_in":3600}"#)
            case ("/rest/v1/stabilis_my_locations", nil, "Bearer second"):
                return (200, #"[{"id":"\#(location.uuidString)","organization_id":"\#(org.uuidString)","name":"Fixture café"}]"#)
            case ("/rest/v1/rpc/stabilis_save_labor_review", nil, "Bearer second"):
                return (400, #"{"code":"40001"}"#)
            case ("/auth/v1/logout", "scope=local", "Bearer second"):
                return (204, "")
            default:
                XCTFail("Unexpected request path \(url.path)")
                return (500, "")
            }
        }
        defer { StubProtocol.handler = nil }
        let initiallyRestored = try await client.restore()
        XCTAssertFalse(initiallyRestored)
        try await client.signIn(email: "fictional@example.invalid", password: "fixture-only")
        let account = await client.userID()
        XCTAssertEqual(account, identity)
        let locations = try await client.locations()
        XCTAssertEqual(locations.first?.organizationId, org)
        XCTAssertEqual(locations.first?.id, location)
        let review = Review(id: UUID(), organizationId: org, locationId: location, weekStart: "2026-11-02",
                            status: "assigned", source: "Fixture", version: 2, inputs: [:], metrics: [:])
        do {
            _ = try await client.save(review, operation: "accept", payload: [:])
            XCTFail("A stale review should require refresh")
        } catch WorkspaceError.stale {}
        try await client.signOut()
        let signedOut = try await client.restore()
        XCTAssertFalse(signedOut)
    }
}

private final class StubProtocol: URLProtocol {
    static var handler: ((URLRequest) throws -> (Int, String))?
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        do {
            guard let handler = Self.handler, let url = request.url else { throw URLError(.badServerResponse) }
            let (status, body) = try handler(request)
            guard let response = HTTPURLResponse(url: url, statusCode: status, httpVersion: nil, headerFields: nil) else {
                throw URLError(.badServerResponse)
            }
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            if !body.isEmpty { client?.urlProtocol(self, didLoad: Data(body.utf8)) }
            client?.urlProtocolDidFinishLoading(self)
        } catch { client?.urlProtocol(self, didFailWithError: error) }
    }
    override func stopLoading() {}
}
