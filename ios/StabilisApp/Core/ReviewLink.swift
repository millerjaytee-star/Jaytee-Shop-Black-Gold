import Foundation

struct ReviewLink: Equatable, Sendable {
    let organization: UUID
    let location: UUID
    let review: UUID

    init(organization: UUID, location: UUID, review: UUID) {
        self.organization = organization
        self.location = location
        self.review = review
    }

    init?(url: URL, webOrigin: URL) {
        guard let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.user == nil, parts.password == nil, parts.query == nil, parts.fragment == nil else { return nil }
        let path = parts.path.split(separator: "/", omittingEmptySubsequences: true)
        let ids: ArraySlice<Substring>
        if parts.scheme == "stabilis", parts.host == "review", parts.port == nil, path.count == 3 {
            ids = path[...]
        } else if parts.scheme == "https", parts.host == webOrigin.host, parts.port == webOrigin.port,
                  path.count == 5, path.prefix(2).elementsEqual(["mobile", "review"]) {
            ids = path.dropFirst(2)
        } else {
            return nil
        }
        let values = ids.compactMap { UUID(uuidString: String($0)) }
        guard values.count == 3 else { return nil }
        self.init(organization: values[0], location: values[1], review: values[2])
    }

    func url(origin: URL) -> URL {
        ["mobile", "review", organization.uuidString.lowercased(), location.uuidString.lowercased(),
         review.uuidString.lowercased()].reduce(origin) { $0.appendingPathComponent($1) }
    }
}
