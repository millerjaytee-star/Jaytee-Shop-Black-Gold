import SwiftUI

@main
@MainActor
struct StabilisApp: App {
    @StateObject private var store: WorkspaceStore

    init() {
        let configuration = Bundle.main
        let publicOrigin = URL(string: "https://stabilis-ops-group.netlify.app")!
        let configuredOrigin = (configuration.object(forInfoDictionaryKey: "StabilisWebOrigin") as? String)
            .flatMap(URL.init(string:))
            .flatMap { url in
                url.scheme == "https" && url.host != nil && url.port == nil &&
                url.user == nil && url.password == nil && url.query == nil && url.fragment == nil &&
                (url.path.isEmpty || url.path == "/") ? url : nil
            }
        let origin = configuredOrigin ?? publicOrigin
        let client: WorkspaceClient?
        if let raw = configuration.object(forInfoDictionaryKey: "StabilisSupabaseURL") as? String,
           let url = URL(string: raw), url.scheme == "https",
           url.host?.hasSuffix(".supabase.co") == true,
           url.user == nil, url.password == nil, url.query == nil, url.fragment == nil,
           url.path.isEmpty || url.path == "/",
           let key = configuration.object(forInfoDictionaryKey: "StabilisSupabasePublishableKey") as? String,
           key.hasPrefix("sb_publishable_") {
            client = WorkspaceClient(baseURL: url, key: key)
        } else {
            client = nil
        }
        let recoveryURL: URL?
        if let raw = configuration.object(forInfoDictionaryKey: "StabilisRecoveryURL") as? String,
           let url = URL(string: raw), url.scheme == "https", url.host == origin.host,
           url.port == origin.port, url.path == "/login",
           url.user == nil, url.password == nil, url.query == nil, url.fragment == nil {
            recoveryURL = url
        } else {
            recoveryURL = nil
        }
        _store = StateObject(wrappedValue: WorkspaceStore(
            client: client, webOrigin: origin, serviceName: "Stabilis",
            recoveryURL: recoveryURL, supportOrigin: publicOrigin
        ))
    }

    var body: some Scene {
        WindowGroup {
            StabilisRootView(store: store)
        }
    }
}
