import SwiftUI

@MainActor
final class NativeProductSession: ObservableObject {
    enum Phase { case opening, signedOut, product }
    let configuration = ZovaConfiguration.bundled
    let api: NativeAPI
    let store: ProductStore
    let signIn = NativeSignIn()
    let social = NativeSignIn()
    @Published var phase: Phase = .opening
    @Published var working = false
    @Published var connectingPlatform: String?
    @Published var message: String?
    @Published var deletionReceipt: URL?
    init() {
        NativeMediaFiles.clear()
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("--test-fresh-install") { try? KeychainVault.clear() }
        if ProcessInfo.processInfo.arguments.contains("--native-fixture") {
            NativeProductFixtures.reset(tiktok: ProcessInfo.processInfo.arguments.contains("--fixture-tiktok"))
            NativeDraftRecovery.remove(owner: "1:0")
            NativeResumeState.saveBrand(0, user: 1); NativeResumeState.saveDraft(nil, user: 1, brand: 0)
            let configuration = URLSessionConfiguration.ephemeral
            configuration.protocolClasses = [NativeProductFixtures.self]
            api = NativeAPI(configuration: .bundled, transport: configuration)
            store = ProductStore(api: api)
            return
        }
        #endif
        api = NativeAPI(configuration: .bundled)
        store = ProductStore(api: api)
    }
    func start() async {
        #if DEBUG
        if ProcessInfo.processInfo.arguments.contains("--native-fixture") {
            try? KeychainVault.save(NativeTokens(access: String(repeating: "a", count: 64), refresh: String(repeating: "r", count: 64), expires: Date().addingTimeInterval(900)))
            do { try await store.start(); phase = .product } catch { message = error.localizedDescription; phase = .signedOut }
            return
        }
        if ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil { phase = .signedOut; return }
        #endif
        await NativeUpgrade.clearLegacyWebDataIfNeeded()
        if !UserDefaults.standard.bool(forKey: "zova-installed") {
            try? KeychainVault.clear(); UserDefaults.standard.set(true, forKey: "zova-installed")
        }
        guard (try? KeychainVault.load()) != nil else { phase = .signedOut; return }
        do { try await api.ensureAvailable(); try await store.start(); phase = .product }
        catch { message = error.localizedDescription; phase = .signedOut }
    }
    func login() async {
        guard !working else { return }; working = true; message = nil; deletionReceipt = nil
        defer { working = false }
        do {
            try await api.ensureAvailable()
            let verifier = try NativeProof.random(48), state = try NativeProof.random()
            let returned = try await signIn.open(configuration: configuration, challenge: NativeProof.challenge(verifier), state: state)
            let code = try NativeProof.code(from: returned, configuration: configuration, state: state)
            try await api.exchange(code: code, verifier: verifier)
            store.signedOut = false; try await store.start(); phase = .product
        } catch { message = error.localizedDescription }
    }
    func logout() async {
        deletionReceipt = nil; store.clear(); await api.logout(); phase = .signedOut
    }
    func reauthenticate() async {
        store.clear(preserveRecovery: true); await api.forget(); phase = .signedOut
        message = "Please sign in again. Any unsaved draft is kept securely for the same account."
    }
    func connect(_ platform: String) async {
        await store.perform {
            guard ProductConnections.canConnect(platform, account: self.store.account) else {
                throw ZovaFailure.server(ProductConnections.facebookNotice)
            }
            self.connectingPlatform = SocialPlatform(rawValue: platform)?.title ?? platform
            defer { self.connectingPlatform = nil }
            try await self.store.save()
            let target = "/connect/\(platform)?workspace=\(self.store.brand)"
            let request = try await self.api.browserHandoff(destination: target)
            guard let url = request.url else { throw ZovaFailure.invalidResponse }
            do {
                let outcome = try await self.social.connect(url: url, destination: target, configuration: self.configuration)
                try await self.store.reloadAccount()
                if outcome == "no_pages" { throw ZovaFailure.server("No Facebook Page was available. Sign in with the Facebook account that manages your Page and allow access to that Page.") }
                if outcome == "connection_failed" { throw ZovaFailure.server("The connection did not finish. Check the account permissions and try again.") }
            } catch ZovaFailure.cancelled { try await self.store.reloadAccount() }
        }
    }
    func returned(_ url: URL) { if social.isActive { social.received(url) } else { signIn.received(url) } }
}

struct NativeProductRoot: View {
    @StateObject private var session = NativeProductSession()
    @Environment(\.scenePhase) private var scenePhase
    @State private var launched = false
    var body: some View {
        ZStack {
            Group {
                switch session.phase {
                case .opening: ZovaDesign.dark.ignoresSafeArea().overlay(ProgressView("Opening Zova…").tint(ZovaDesign.violet).foregroundStyle(.white))
                case .signedOut: welcome
                case .product: NativeProductTabs(session: session).environmentObject(session.store)
                }
            }
            if !launched { ZovaLaunchScreen(ready: session.phase != .opening) { launched = true }.zIndex(1) }
            if scenePhase != .active { ZovaDesign.dark.ignoresSafeArea().overlay(Image("ZovaMark").resizable().scaledToFit().frame(width: 72)).zIndex(2).accessibilityHidden(true) }
        }.task { await session.start() }.onOpenURL { session.returned($0) }
            .onContinueUserActivity(NSUserActivityTypeBrowsingWeb) { if let url = $0.webpageURL { session.returned(url) } }
            .onChange(of: scenePhase) { _, phase in
                if phase == .background { Task { await session.store.perform { try await session.store.save() } } }
                if phase == .active, session.phase == .product { Task { await session.store.perform { try await session.store.reloadAccount() } } }
            }
    }
    private var welcome: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack { Image("ZovaMark").resizable().scaledToFit().frame(width: 40); Text("Zova").font(.largeTitle.bold()) }
                Text("Because content\nis the fun part.").font(.largeTitle.bold()).fixedSize(horizontal: false, vertical: true)
                Text("Turn your ideas into captions and a content plan with Zova, your AI social media manager.").font(.title3).foregroundStyle(.white.opacity(0.75))
                signInButton
                welcomeLinks
                Text("Use your existing Zova account, or create one in the secure sign-in window.").font(.subheadline).foregroundStyle(.white.opacity(0.75))
                Text("When you ask for AI help, your idea and selected images or video frames are sent to OpenAI. Audio isn’t analysed.").font(.footnote).foregroundStyle(.white.opacity(0.75))
                if let message = session.message { Text(message).font(.callout).accessibilityAddTraits(.updatesFrequently) }
                if let receipt = session.deletionReceipt {
                    Link(destination: receipt) {
                        Text("View deletion status").frame(minHeight: 44).contentShape(Rectangle())
                    }
                        .accessibilityIdentifier("deletion-receipt")
                }
                Text(buildLabel).font(.caption).foregroundStyle(.secondary)
            }.padding(28).frame(maxWidth: 560)
        }.background(ZovaDesign.dark).foregroundStyle(.white).preferredColorScheme(.dark)
    }
    private var signInButton: some View {
        Button { Task { await session.login() } } label: {
            HStack {
                if session.working { ProgressView().tint(.white) }
                Text(session.working ? "Opening sign-in…" : "Continue to Zova")
            }
        }.buttonStyle(ZovaPrimary()).disabled(session.working).accessibilityIdentifier("continue-zova")
    }
    private var welcomeLinks: some View {
        NativeAdaptiveRow(spacing: 24) {
            welcomeLink("Privacy", path: "/privacy-policy")
            welcomeLink("Terms", path: "/terms-of-service")
            welcomeLink("Help", path: "/help")
        }.tint(ZovaDesign.violet)
    }
    private func welcomeLink(_ title: String, path: String) -> some View {
        Button { if let url = try? session.configuration.endpoint(path) { UIApplication.shared.open(url) } } label: { Text(title).frame(minWidth: 44, minHeight: 44).contentShape(Rectangle()) }
    }
    private var buildLabel: String {
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? ""
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? ""
        return "Version \(version) (\(build))"
    }
}

struct NativeProductTabs: View {
    @Environment(\.scenePhase) private var scenePhase
    @ObservedObject var session: NativeProductSession
    @EnvironmentObject var store: ProductStore
    @State private var nextMove = false
    @State private var strategy = false
    @State private var keyboard = false
    private let tabs = [("Studio", "square.and.pencil"), ("Schedule", "calendar"), ("Performance", "chart.bar"), ("Account", "person.crop.circle")]
    var body: some View {
        VStack(spacing: 0) {
            NativeProductPages(session: session, nextMove: $nextMove, strategy: $strategy).id(store.brand)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            if !keyboard {
                HStack(spacing: 0) {
                    ForEach(tabs.indices, id: \.self) { index in
                        Button {
                            Task { await store.perform { try await store.save(); store.selectedTab = index } }
                        } label: {
                            VStack(spacing: 5) {
                                Image(systemName: tabs[index].1).font(.system(size: 22))
                                Text(tabs[index].0).font(.caption).dynamicTypeSize(...DynamicTypeSize.large).lineLimit(1)
                            }
                                .frame(maxWidth: .infinity, minHeight: 58).foregroundStyle(store.selectedTab == index ? ZovaDesign.violet : .white.opacity(0.8))
                        }.accessibilityLabel(tabs[index].0)
                            .accessibilityAddTraits(store.selectedTab == index ? .isSelected : [])
                            .accessibilityShowsLargeContentViewer { Label(tabs[index].0, systemImage: tabs[index].1) }
                            .accessibilityIdentifier("tab-" + tabs[index].0).disabled(store.busy)
                    }
                }.padding(.horizontal, 6).background(ZovaDesign.dark.ignoresSafeArea(edges: .bottom))
            }
        }.background(store.selectedTab == 3 ? ZovaDesign.dark : .white).preferredColorScheme(store.selectedTab == 3 ? .dark : .light)
            .tint(ZovaDesign.purple).background(NativeKeyboardDismiss().allowsHitTesting(false))
            .sheet(isPresented: $nextMove) { NativeNextMoveView().environmentObject(store) }
            .sheet(isPresented: $strategy) { NativeNextMoveView(planning: true).environmentObject(store) }
            .sheet(isPresented: $store.showReview) { NativePublishView(mode: store.reviewMode, connect: { await session.connect($0) }).environmentObject(store).interactiveDismissDisabled(store.busy) }
            .sheet(isPresented: $store.needsConsent) { NativeAIConsentView().environmentObject(store) }
            .sheet(isPresented: $store.showIntro) { NativeGuideView(introduction: true).environmentObject(store) }
            .alert("Zova", isPresented: Binding(get: { store.error != nil }, set: { if !$0 { store.error = nil } })) { Button("OK") { store.error = nil } } message: { Text(store.error ?? "") }
            .onChange(of: store.signedOut) { _, value in if value { Task { await session.reauthenticate() } } }
            .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillShowNotification)) { _ in keyboard = true }
            .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillHideNotification)) { _ in keyboard = false }
            .task(id: scenePhase) {
                guard scenePhase == .active else { return }
                while !Task.isCancelled {
                    await store.refreshConnections()
                    do { try await Task.sleep(for: .seconds(60)) } catch { return }
                }
            }
    }
}

/// Keep edits and scroll positions when moving between tabs. A brand change
/// replaces this container so no other brand's UI state can remain visible.
private struct NativeProductPages: View {
    @ObservedObject var session: NativeProductSession
    @EnvironmentObject var store: ProductStore
    @Binding var nextMove: Bool
    @Binding var strategy: Bool
    @State private var visited: Set<Int> = [0]
    var body: some View {
        ZStack {
            ForEach(visited.sorted(), id: \.self) { index in
                page(index).opacity(store.selectedTab == index ? 1 : 0)
                    .allowsHitTesting(store.selectedTab == index).accessibilityHidden(store.selectedTab != index)
            }
        }.onChange(of: store.selectedTab) { _, index in visited.insert(index) }
    }
    @ViewBuilder private func page(_ index: Int) -> some View {
        switch index {
        case 0: NativeStudioView(nextMove: $nextMove, strategy: $strategy)
        case 1: NativeScheduleView()
        case 2: NativePerformanceView()
        default: NativeAccountView(session: session, strategy: $strategy)
        }
    }
}
