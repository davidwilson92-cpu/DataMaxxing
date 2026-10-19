import SwiftUI
import WebKit

@MainActor
final class ZovaSession: ObservableObject {
    enum Phase { case opening, signedOut, studio }
    @Published var phase: Phase = .opening
    @Published var working = false
    @Published var message: String?
    @Published var cookieReady = false
    let configuration = ZovaConfiguration.bundled
    lazy var api = NativeAPI(configuration: configuration)
    let signIn = NativeSignIn()
    let pages = [StudioPage("/studio"), StudioPage("/drafts"), StudioPage("/analytics"), StudioPage("/account")]
    func start() async {
        if !UserDefaults.standard.bool(forKey: "zova-installed") {
            try? KeychainVault.clear()
            await clearWebData()
            UserDefaults.standard.set(true, forKey: "zova-installed")
        }
        do {
            guard try KeychainVault.load() != nil else { phase = .signedOut; return }
            try await api.ensureAvailable()
            pages[0].load(try await api.handoff(destination: "/studio"))
            phase = .studio
        } catch ZovaFailure.signInRequired { await didSignOut() }
        catch { message = error.localizedDescription; phase = .signedOut }
    }
    func login() async {
        guard !working else { return }
        working = true; message = nil
        defer { working = false }
        do {
            try await api.ensureAvailable()
            let verifier = try NativeProof.random(48), state = try NativeProof.random()
            let url = try await signIn.open(configuration: configuration, challenge: NativeProof.challenge(verifier), state: state)
            let code = try NativeProof.code(from: url, configuration: configuration, state: state)
            try await api.exchange(code: code, verifier: verifier)
            await clearWebData()
            pages[0].load(try await api.handoff(destination: "/studio"))
            cookieReady = false; phase = .studio
        } catch { message = error.localizedDescription }
    }
    func loaded() {
        guard !cookieReady else { return }
        cookieReady = true
        for page in pages.dropFirst() {
            if let url = try? configuration.endpoint(page.path) { page.load(URLRequest(url: url)) }
        }
    }
    func didSignOut() async {
        await api.forget()
        await clearWebData()
        for page in pages { page.request = nil; page.webView?.loadHTMLString("", baseURL: nil) }
        cookieReady = false; phase = .signedOut
    }
    func logout() async { await api.logout(); await didSignOut() }
    private func clearWebData() async {
        await withCheckedContinuation { continuation in
            WKWebsiteDataStore.default().removeData(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes(), modifiedSince: .distantPast) { continuation.resume() }
        }
    }
}

struct LinkSheet: Identifiable { let id = UUID(); let url: URL }

struct ZovaRoot: View {
    @StateObject private var model = ZovaSession()
    @Environment(\.scenePhase) private var scenePhase
    @State private var selected = 0
    @State private var keyboard = false
    @State private var browser: LinkSheet?
    @State private var exported: LinkSheet?
    @State private var exportToRemove: URL?
    @State private var browserBusy = false
    private let titles = ["Studio", "Drafts", "Performance", "Account"]
    private let icons = ["square.and.pencil", "doc.on.doc", "chart.bar", "person.crop.circle"]
    private let purple = Color(red: 0.486, green: 0.227, blue: 0.929)
    var body: some View {
        ZStack {
            Color.white.ignoresSafeArea()
            switch model.phase {
            case .opening: ProgressView("Opening Zova…").tint(purple)
            case .signedOut: welcome
            case .studio: studio
            }
            if scenePhase != .active {
                Color(red: 0.05, green: 0.05, blue: 0.07).ignoresSafeArea()
                Image("ZovaMark").resizable().scaledToFit().frame(width: 72, height: 72).accessibilityHidden(true)
            }
        }
        .task { await model.start() }
        .onOpenURL { model.signIn.received($0) }
        .onContinueUserActivity(NSUserActivityTypeBrowsingWeb) { if let url = $0.webpageURL { model.signIn.received(url) } }
        .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillShowNotification)) { _ in keyboard = true }
        .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillHideNotification)) { _ in keyboard = false }
        .sheet(item: $browser, onDismiss: { model.pages.forEach { $0.refreshConnections() } }) { link in
            BrowserSheet(url: link.url) { browser = nil }
                .ignoresSafeArea()
        }
        .sheet(item: $exported, onDismiss: clearExport) { link in ExportSheet(file: link.url) }
    }
    private var welcome: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack(spacing: 12) {
                    Image("ZovaMark").resizable().scaledToFit().frame(width: 48, height: 48)
                    Text("Zova").font(.system(size: 32, weight: .bold))
                }.padding(.top, 48)
                Text("Your AI social manager.").font(.headline).foregroundStyle(purple)
                Text("Your ideas.\nStill you.").font(.system(size: 48, weight: .bold, design: .rounded)).minimumScaleFactor(0.65)
                Text("Shape your next post, plan your socials and share in your voice.")
                    .font(.title3).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                Button { Task { await model.login() } } label: {
                    HStack { Spacer(); if model.working { ProgressView().tint(.white) }; Text(model.working ? "Opening sign-in…" : "Continue to Zova").fontWeight(.semibold); Spacer() }
                        .padding(18).background(LinearGradient(colors: [purple, Color(red: 0.36, green: 0.13, blue: 0.71)], startPoint: .topLeading, endPoint: .bottomTrailing), in: RoundedRectangle(cornerRadius: 18)).foregroundStyle(.white)
                }.disabled(model.working).accessibilityIdentifier("continue-zova")
                Text("Use your existing Zova account, or create one in the secure sign-in window.").font(.subheadline).foregroundStyle(.secondary)
                Text("When you ask for AI help, your idea and selected images or video frames are sent to OpenAI. Audio isn’t analysed.").font(.footnote).foregroundStyle(.secondary)
                if let message = model.message { Text(message).font(.callout).foregroundStyle(.primary).accessibilityAddTraits(.updatesFrequently) }
                HStack(spacing: 24) {
                    Button("Privacy") { openLegal("/privacy-policy") }
                    Button("Terms") { openLegal("/terms-of-service") }
                    Button("Help") { openLegal("/help") }
                }.font(.subheadline).tint(purple).frame(minHeight: 44)
                Text("Beta access • No purchases in this app").font(.footnote).foregroundStyle(.secondary)
            }.padding(28).frame(maxWidth: 560)
        }
    }
    private var studio: some View {
        VStack(spacing: 0) {
            ZStack {
                ForEach(model.pages.indices, id: \.self) { index in
                    pageView(index).opacity(index == selected ? 1 : 0)
                        .allowsHitTesting(index == selected).accessibilityHidden(index != selected)
                }
            }
            if !keyboard {
                HStack(spacing: 0) {
                    ForEach(titles.indices, id: \.self) { index in
                        Button { selected = index } label: {
                            VStack(spacing: 5) {
                                Image(systemName: icons[index]).font(.system(size: 21, weight: .medium))
                                Text(titles[index]).font(.caption2.weight(.medium))
                            }.frame(maxWidth: .infinity).frame(minHeight: 58)
                                .foregroundStyle(index == selected ? Color(red: 0.73, green: 0.56, blue: 1) : .white.opacity(0.8))
                        }.disabled(!model.cookieReady).accessibilityLabel(titles[index])
                            .accessibilityAddTraits(index == selected ? .isSelected : [])
                    }
                }.background(Color(red: 0.05, green: 0.05, blue: 0.07))
            }
        }
    }
    private func pageView(_ index: Int) -> some View {
        ObservedStudioPage(page: model.pages[index], configuration: model.configuration, browserBusy: browserBusy) {
            StudioSurface(page: model.pages[index], configuration: model.configuration,
                          ready: { model.loaded() }, signedOut: { Task { await model.didSignOut() } },
                          browser: { destination in Task { await openAccount(destination) } },
                          external: openExternal, share: { exportToRemove = $0; exported = LinkSheet(url: $0) })
        }
    }
    private func openLegal(_ path: String) { if let url = try? model.configuration.endpoint(path) { browser = LinkSheet(url: url) } }
    private func openExternal(_ url: URL) {
        if url.scheme == "https" { browser = LinkSheet(url: url) }
        else if ["mailto", "tel"].contains(url.scheme ?? "") { UIApplication.shared.open(url) }
    }
    private func openAccount(_ destination: String) async {
        guard !browserBusy else { return }
        browserBusy = true
        defer { browserBusy = false }
        do { let request = try await model.api.handoff(destination: destination, browser: true); if let url = request.url { browser = LinkSheet(url: url) } }
        catch { model.pages[selected].failure = error.localizedDescription }
    }
    private func clearExport() {
        // Export files live in a per-download temporary directory; never delete user uploads.
        guard let file = exportToRemove else { return }
        let directory = file.deletingLastPathComponent().standardizedFileURL
        if directory.deletingLastPathComponent() == FileManager.default.temporaryDirectory.standardizedFileURL,
           directory.lastPathComponent.hasPrefix("zova-export-") { try? FileManager.default.removeItem(at: directory) }
        exportToRemove = nil
    }
}

private struct ObservedStudioPage<Content: View>: View {
    @ObservedObject var page: StudioPage
    let configuration: ZovaConfiguration
    let browserBusy: Bool
    @ViewBuilder let content: () -> Content
    var body: some View {
        ZStack(alignment: .top) {
            content()
            if page.loading || browserBusy { ProgressView().padding(10).background(.regularMaterial, in: Capsule()).padding(6) }
            if let failure = page.failure {
                VStack(spacing: 12) {
                    Text(failure).font(.callout).multilineTextAlignment(.center)
                    Button("Open saved work") { page.recover(configuration) }.buttonStyle(.borderedProminent)
                    Button("Dismiss") { page.failure = nil }
                }.padding(20).background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20)).padding(20)
            }
        }
    }
}

@main
struct ZovaApp: App {
    var body: some Scene { WindowGroup { ZovaRoot().preferredColorScheme(.light) } }
}
