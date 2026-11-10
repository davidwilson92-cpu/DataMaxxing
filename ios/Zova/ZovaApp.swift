import SwiftUI

@main
struct ZovaApp: App {
    var body: some Scene {
        WindowGroup {
            #if DEBUG
            if ProcessInfo.processInfo.arguments.contains("--test-launch-screen") {
                LaunchScreenTestHost()
            } else {
                NativeProductRoot()
            }
            #else
            NativeProductRoot()
            #endif
        }
    }
}
