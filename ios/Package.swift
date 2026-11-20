// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "StabilisWorkspace",
    platforms: [.macOS(.v13), .iOS(.v17)],
    targets: [
        .target(name: "WorkspaceCore", path: "StabilisApp/Core"),
        .testTarget(name: "WorkspaceCoreTests", dependencies: ["WorkspaceCore"], path: "Tests")
    ]
)
