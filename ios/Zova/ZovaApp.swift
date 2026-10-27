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
                    .modifier(NativeTestTextSize())
            }
            #else
            NativeProductRoot()
            #endif
        }
    }
}

#if DEBUG
/// UI-test-only environment: exercises real SwiftUI Dynamic Type layout. Never
/// overrides the system's text preference in a release build.
private struct NativeTestTextSize: ViewModifier {
    func body(content: Content) -> some View {
        if ProcessInfo.processInfo.arguments.contains("--accessibility-text") {
            content.environment(\.dynamicTypeSize, .accessibility5)
        } else { content }
    }
}
#endif
