// Native cookie installation completes before any Studio GET is loaded.
import SwiftUI
import WebKit
import SafariServices

@MainActor
enum StudioBootstrap {
    static func request(_ session: NativeWebSession, store: WKHTTPCookieStore = WKWebsiteDataStore.default().httpCookieStore) async throws -> URLRequest {
        let existing = await store.allCookies()
        for cookie in existing where cookie.name == "zova_brand" && cookie.domain == session.cookie.domain {
            await store.deleteCookie(cookie)
        }
        await store.setCookie(session.cookie)
        guard await store.allCookies().contains(where: { $0.name == session.cookie.name && $0.domain == session.cookie.domain && $0.value == session.cookie.value }) else {
            throw ZovaFailure.secureStorage
        }
        return URLRequest(url: session.url, cachePolicy: .reloadIgnoringLocalCacheData)
    }
}

@MainActor
final class StudioPage: ObservableObject {
    let path: String
    @Published var loading = false
    @Published var failure: String?
    @Published var request: URLRequest?
    @Published var requestID = UUID()
    weak var webView: WKWebView?
    init(_ path: String) { self.path = path }
    func load(_ request: URLRequest) { self.request = request; requestID = UUID(); failure = nil }
    func recover(_ configuration: ZovaConfiguration) {
        let candidate = webView?.url
        let allowed = ["/studio", "/drafts", "/account", "/analytics", "/security"]
        let url = candidate.flatMap { configuration.owns($0) && allowed.contains($0.path) ? $0 : nil }
        if let target = url ?? (try? configuration.endpoint(path)) { load(URLRequest(url: target)) }
    }
    func refreshConnections() {
        guard let url = webView?.url, ZovaConfiguration.bundled.owns(url) else { return }
        webView?.evaluateJavaScript("if(typeof refreshNativeConnections==='function'){refreshNativeConnections();}", completionHandler: nil)
    }
}

struct StudioSurface: UIViewRepresentable {
    @ObservedObject var page: StudioPage
    let configuration: ZovaConfiguration
    var ready: () -> Void
    var signedOut: () -> Void
    var browser: (String) -> Void
    var external: (URL) -> Void
    var share: (URL) -> Void
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeUIView(context: Context) -> WKWebView {
        let settings = WKWebViewConfiguration()
        settings.websiteDataStore = .default()
        settings.allowsInlineMediaPlayback = true
        settings.mediaTypesRequiringUserActionForPlayback = .all
        settings.defaultWebpagePreferences.allowsContentJavaScript = true
        let view = WKWebView(frame: .zero, configuration: settings)
        view.navigationDelegate = context.coordinator
        view.uiDelegate = context.coordinator
        view.isOpaque = false
        view.backgroundColor = page.path == "/account" ? UIColor(red: 0.031, green: 0.024, blue: 0.059, alpha: 1) : .white
        view.scrollView.backgroundColor = view.backgroundColor
        view.scrollView.contentInsetAdjustmentBehavior = .never
        view.allowsBackForwardNavigationGestures = true
        view.isInspectable = false
        view.customUserAgent = nil
        page.webView = view
        return view
    }
    func updateUIView(_ view: WKWebView, context: Context) {
        context.coordinator.parent = self
        guard let request = page.request, context.coordinator.loaded != page.requestID else { return }
        context.coordinator.loaded = page.requestID
        view.load(request)
    }
    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
        var parent: StudioSurface
        var loaded: UUID?
        private var downloads: [ObjectIdentifier: URL] = [:]
        init(_ parent: StudioSurface) { self.parent = parent }
        func webView(_ view: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            parent.page.loading = true
        }
        func webView(_ view: WKWebView, didFinish navigation: WKNavigation!) {
            parent.page.loading = false
            guard let url = view.url, parent.configuration.owns(url) else { return }
            guard url.path != "/mobile/web-session" else {
                parent.page.failure = "Studio couldn’t finish signing in. Close and reopen Zova to try again."
                return
            }
            parent.page.failure = nil
            if url.path == "/login" || url.path == "/" {
                parent.signedOut(); return
            }
            parent.ready()
        }
        func webView(_ view: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { failed(error) }
        func webView(_ view: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { failed(error) }
        private func failed(_ error: Error) {
            parent.page.loading = false
            if (error as NSError).code != NSURLErrorCancelled {
                parent.page.failure = "Can’t connect to Zova. Your saved work is still on your account."
            }
        }
        func webViewWebContentProcessDidTerminate(_ view: WKWebView) {
            parent.page.loading = false
            parent.page.failure = "Studio paused. Reopen your saved work to continue."
        }
        func webView(_ view: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = action.request.url else { decisionHandler(.cancel); return }
            if let destination = parent.configuration.browserDestination(url) {
                decisionHandler(.cancel); parent.browser(destination); return
            }
            if action.shouldPerformDownload && (parent.configuration.owns(url) || url.absoluteString.hasPrefix("blob:" + parent.configuration.base.absoluteString)) {
                decisionHandler(.download); return
            }
            if parent.configuration.owns(url) {
                if url.path.hasPrefix("/billing/") || url.path == "/subscribe" {
                    parent.page.failure = "Purchases are unavailable in the iPhone beta."
                    decisionHandler(.cancel); return
                }
                decisionHandler(.allow); return
            }
            if url.absoluteString == "about:blank" { decisionHandler(.allow); return }
            decisionHandler(.cancel)
            if action.navigationType == .linkActivated && ["https", "mailto", "tel"].contains(url.scheme ?? "") {
                parent.external(url)
            }
        }
        func acceptResponse(_ response: URLResponse) -> Bool {
            if let http = response as? HTTPURLResponse, http.statusCode == 401 {
                parent.signedOut(); return false
            }
            let badStatus = (response as? HTTPURLResponse).map { $0.statusCode >= 400 } ?? false
            let download = (response as? HTTPURLResponse)?.value(forHTTPHeaderField: "Content-Disposition")?.lowercased().hasPrefix("attachment") ?? false
            if badStatus || (response.mimeType == "application/json" && !download) || response.url?.path == "/mobile/web-session" {
                parent.page.loading = false
                parent.page.failure = "Studio couldn’t open securely. Close and reopen Zova to try again."
                return false
            }
            return true
        }
        func webView(_ view: WKWebView, decidePolicyFor response: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
            guard !response.isForMainFrame || acceptResponse(response.response) else { decisionHandler(.cancel); return }
            decisionHandler(response.canShowMIMEType ? .allow : .download)
        }
        func webView(_ view: WKWebView, createWebViewWith configuration: WKWebViewConfiguration, for action: WKNavigationAction, windowFeatures: WKWindowFeatures) -> WKWebView? {
            guard let url = action.request.url else { return nil }
            if let destination = parent.configuration.browserDestination(url) { parent.browser(destination) }
            else if parent.configuration.owns(url) { view.load(action.request) }
            else if url.scheme == "https" { parent.external(url) }
            return nil
        }
        func webView(_ view: WKWebView, runJavaScriptAlertPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping () -> Void) {
            let alert = UIAlertController(title: "Zova", message: String(message.prefix(1000)), preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "OK", style: .default) { _ in completionHandler() })
            present(alert, fallback: completionHandler)
        }
        func webView(_ view: WKWebView, runJavaScriptConfirmPanelWithMessage message: String, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
            let alert = UIAlertController(title: "Zova", message: String(message.prefix(1000)), preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "Cancel", style: .cancel) { _ in completionHandler(false) })
            alert.addAction(UIAlertAction(title: "Continue", style: .default) { _ in completionHandler(true) })
            present(alert) { completionHandler(false) }
        }
        private func present(_ alert: UIAlertController, fallback: () -> Void) {
            guard var controller = parent.page.webView?.window?.rootViewController else { fallback(); return }
            while let presented = controller.presentedViewController { controller = presented }
            controller.present(alert, animated: true)
        }
        func webView(_ view: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) { download.delegate = self }
        func webView(_ view: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) { download.delegate = self }
        func download(_ download: WKDownload, decideDestinationUsing response: URLResponse, suggestedFilename: String, completionHandler: @escaping (URL?) -> Void) {
            guard let url = response.url, parent.configuration.owns(url) || url.scheme == "blob" else { completionHandler(nil); return }
            let name = URL(fileURLWithPath: suggestedFilename).lastPathComponent
                .replacingOccurrences(of: "[^A-Za-z0-9._ -]", with: "_", options: .regularExpression)
            let directory = FileManager.default.temporaryDirectory.appendingPathComponent("zova-export-" + UUID().uuidString)
            do {
                try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.protectionKey: FileProtectionType.complete])
                let target = directory.appendingPathComponent(String(name.prefix(160)).isEmpty ? "Zova-export" : String(name.prefix(160)))
                downloads[ObjectIdentifier(download)] = target
                completionHandler(target)
            } catch { completionHandler(nil); parent.page.failure = "This file couldn’t be saved. Please try again." }
        }
        func downloadDidFinish(_ download: WKDownload) {
            if let url = downloads.removeValue(forKey: ObjectIdentifier(download)) { parent.share(url) }
        }
        func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
            if let url = downloads.removeValue(forKey: ObjectIdentifier(download)) { try? FileManager.default.removeItem(at: url.deletingLastPathComponent()) }
            parent.page.failure = "The download didn’t finish. Please try again."
        }
    }
}

struct BrowserSheet: UIViewControllerRepresentable {
    let url: URL
    var finished: () -> Void
    func makeCoordinator() -> Coordinator { Coordinator(finished) }
    func makeUIViewController(context: Context) -> SFSafariViewController {
        let view = SFSafariViewController(url: url)
        view.delegate = context.coordinator
        view.preferredControlTintColor = UIColor(red: 0.49, green: 0.23, blue: 0.93, alpha: 1)
        view.dismissButtonStyle = .done
        return view
    }
    func updateUIViewController(_ controller: SFSafariViewController, context: Context) { }
    final class Coordinator: NSObject, SFSafariViewControllerDelegate {
        let finished: () -> Void
        init(_ finished: @escaping () -> Void) { self.finished = finished }
        func safariViewControllerDidFinish(_ controller: SFSafariViewController) { finished() }
    }
}

struct ExportSheet: UIViewControllerRepresentable {
    let file: URL
    func makeUIViewController(context: Context) -> UIActivityViewController { UIActivityViewController(activityItems: [file], applicationActivities: nil) }
    func updateUIViewController(_ controller: UIActivityViewController, context: Context) { }
}
