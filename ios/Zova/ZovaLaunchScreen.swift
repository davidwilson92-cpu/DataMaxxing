import SwiftUI

/// App-owned animation after iOS's static launch screen. It never gates startup work.
struct ZovaLaunchScreen: View {
    let ready: Bool
    var motionOverride: Bool? = nil
    let finished: () -> Void
    @Environment(\.accessibilityReduceMotion) private var systemReduceMotion
    private var reduceMotion: Bool { motionOverride ?? systemReduceMotion }
    @State private var appeared = false
    @State private var departing = false
    @State private var zooming = false
    @State private var faded = false
    @State private var slow = false
    @State private var started = ContinuousClock.now
    private let night = Color(red: 0.031, green: 0.024, blue: 0.059)

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                night
                RadialGradient(colors: [Color(red: 0.24, green: 0.10, blue: 0.40).opacity(0.55), night],
                               center: .center, startRadius: 0, endRadius: min(geometry.size.width, geometry.size.height) * 0.8)
                VStack(spacing: 16) {
                    // Preserve the exact brand mark; the image zooms beyond the viewport.
                    Image("ZovaMark").resizable().scaledToFit().frame(width: 104, height: 104)
                        .scaleEffect(zooming && !reduceMotion ? max(geometry.size.width, geometry.size.height) / 104 * 3 : (appeared || reduceMotion ? 1 : 0.94))
                        .opacity(appeared ? 1 : 0)
                        .zIndex(1)
                        .accessibilityHidden(true)
                    VStack(spacing: 8) {
                        Text("Zova").font(.system(size: 36, weight: .bold)).foregroundStyle(.white)
                        Text("Your AI social manager.").font(.system(size: 17, weight: .medium))
                            .foregroundStyle(Color(red: 0.80, green: 0.74, blue: 0.89))
                    }.opacity(appeared && !departing ? 1 : 0)
                }.padding(24).frame(maxWidth: .infinity, maxHeight: .infinity)
                if slow && !departing {
                    Text("Opening your workspace…").font(.footnote).foregroundStyle(.white.opacity(0.7))
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .bottom).padding(.bottom, 64)
                }
            }
            .clipped()
            .opacity(faded ? 0 : 1)
        }
        .ignoresSafeArea()
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Zova. Your AI social manager. Loading.")
        .accessibilityIdentifier("zova-launch")
        .task {
            started = .now
            withAnimation(.easeOut(duration: reduceMotion ? 0.15 : 0.28)) { appeared = true }
            do {
                try await Task.sleep(for: .seconds(3))
                slow = true
                // Reveal existing loading/recovery UI if the network takes too long.
                try await Task.sleep(for: .seconds(5))
                finish(zoom: false)
            } catch { /* Removal cancels the watchdog. */ }
        }
        .task(id: ready) {
            guard ready else { return }
            do {
                if !reduceMotion {
                    try await ContinuousClock().sleep(until: started.advanced(by: .milliseconds(300)))
                }
                try Task.checkCancellation()
                finish(zoom: !reduceMotion)
            } catch { /* Readiness changed or the cover was removed. */ }
        }
    }

    private func finish(zoom: Bool) {
        guard !departing else { return }
        withAnimation(.easeInOut(duration: zoom ? 0.62 : 0.2)) { departing = true; zooming = zoom }
        withAnimation(.easeIn(duration: zoom ? 0.32 : 0.2).delay(zoom ? 0.30 : 0), completionCriteria: .removed) {
            faded = true
        } completion: {
            finished()
        }
    }
}

#if DEBUG
/// Deterministic UI-test host; never built into the distributed app.
struct LaunchScreenTestHost: View {
    @State private var ready = false
    @State private var covered = true
    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()
            Text("Launch destination").foregroundStyle(.black).accessibilityIdentifier("launch-destination")
                .accessibilityHidden(covered)
            if covered {
                ZovaLaunchScreen(ready: ready, motionOverride: ProcessInfo.processInfo.arguments.contains("--launch-reduce-motion")) { covered = false }
            }
        }
        .task {
            guard !ProcessInfo.processInfo.arguments.contains("--launch-never-ready") else { return }
            try? await Task.sleep(for: .seconds(4))
            ready = true
        }
    }
}
#endif
