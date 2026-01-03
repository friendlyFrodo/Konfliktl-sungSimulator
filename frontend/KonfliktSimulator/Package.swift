// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "KonfliktSimulator",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "KonfliktSimulator", targets: ["KonfliktSimulator"])
    ],
    targets: [
        .executableTarget(
            name: "KonfliktSimulator",
            path: "Sources/KonfliktSimulator"
        )
    ]
)
