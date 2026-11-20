import SwiftUI

@main
@MainActor
struct StabilisApp: App {
    @StateObject private var store: WorkspaceStore

    init() {
        let configuration = Bundle.main
        let origin = URL(string: "https://stabilis-ops-group.netlify.app")!
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
        _store = StateObject(wrappedValue: WorkspaceStore(client: client, webOrigin: origin, serviceName: "Stabilis"))
    }

    var body: some Scene {
        WindowGroup {
            StabilisRootView(store: store)
        }
    }
}
