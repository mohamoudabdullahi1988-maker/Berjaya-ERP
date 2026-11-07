// swift-tools-version: 5.9
import PackageDescription
let package = Package(name: "SidraHomes", platforms: [.macOS(.v13)], products: [.executable(name: "SidraHomes", targets: ["SidraHomes"])], targets: [.executableTarget(name: "SidraHomes")], swiftLanguageVersions: [.v5])
