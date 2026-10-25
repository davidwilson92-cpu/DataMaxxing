import XCTest
import WebKit
import Network
@testable import Zova

// Exercise WebKit's actual network process, not just URLSession mocks. The
// listener is loopback-only and uses disposable synthetic credentials.
@MainActor
final class WebKitHandoffTests: XCTestCase {
    func testExportCompletionRequiresOriginalReadySessionAndCleansStaleFiles() throws {
        let page = StudioPage("/studio")
        var authority: Int? = nil
        var shared: [URL] = []
        let surface = StudioSurface(page: page, configuration: try ZovaConfiguration(base: URL(string: "https://zova-social.com")!), ready: {}, signedOut: {}, browser: { _ in }, external: { _ in }, share: { shared.append($0) }, exportEpoch: 4, exportAuthority: { authority })
        let coordinator = surface.makeCoordinator()
        func file() throws -> URL {
            let folder = FileManager.default.temporaryDirectory.appendingPathComponent("zova-export-" + UUID().uuidString)
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            let url = folder.appendingPathComponent("synthetic.txt")
            try Data("Synthetic private export".utf8).write(to: url)
            return url
        }
        // Coordinator was created before the cookie became ready; this must not
        // permanently disable exports from the same successfully opened session.
        authority = 4
        let valid = try file()
        coordinator.finishExport(valid)
        XCTAssertEqual(shared, [valid])
        StudioExport.remove(valid)
        for replacement in [nil, 5] as [Int?] {
            authority = replacement
            let stale = try file()
            coordinator.finishExport(stale)
            XCTAssertEqual(shared, [valid], "Never share an earlier account's late download")
            XCTAssertFalse(FileManager.default.fileExists(atPath: stale.deletingLastPathComponent().path))
        }
        let unrelated = FileManager.default.temporaryDirectory.appendingPathComponent("keep-" + UUID().uuidString)
        try Data("Keep unrelated temporary data".utf8).write(to: unrelated)
        defer { try? FileManager.default.removeItem(at: unrelated) }
        StudioExport.remove(unrelated)
        XCTAssertTrue(FileManager.default.fileExists(atPath: unrelated.path))
    }

    func testStudioNavigationWaitsForPersistenceAndRejectsBusyOrLateChanges() async throws {
        let configuration = try ZovaConfiguration(base: URL(string: "https://zova-social.com")!)
        let loaded = expectation(description: "Synthetic Studio document loaded")
        let settings = WKWebViewConfiguration()
        settings.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: CGRect(x: 0, y: 0, width: 390, height: 844), configuration: settings)
        let navigation = StudioGuardProbeNavigation(loaded)
        view.navigationDelegate = navigation
        view.loadHTMLString("""
            <!doctype html><html><body>Disposable Studio fixture<script>
            let studioLoading=false, mediaUploading=false, sendingMessage=false;
            let savedSerial=0, changeSerial=1, saveCalls=0;
            async function saveDraftNow() {
                await new Promise(resolve=>setTimeout(resolve,10));
                saveCalls++; savedSerial=changeSerial;
            }
            </script></body></html>
            """, baseURL: URL(string: "https://zova-social.com/studio")!)
        await fulfillment(of: [loaded], timeout: 30)
        XCTAssertEqual(view.url?.path, "/studio")
        let page = StudioPage("/studio")
        page.webView = view
        for busy in ["mediaUploading", "sendingMessage", "studioLoading"] {
            _ = try await view.evaluateJavaScript("\(busy)=true; true")
            let allowed = try await page.saveBeforeNavigation(configuration)
            XCTAssertFalse(allowed, "Must keep Studio while \(busy)")
            _ = try await view.evaluateJavaScript("\(busy)=false; true")
        }
        let callsBeforeSave = try await view.evaluateJavaScript("saveCalls")
        XCTAssertEqual(callsBeforeSave as? Int, 0)
        let saved = try await page.saveBeforeNavigation(configuration)
        XCTAssertTrue(saved)
        let state = try await view.evaluateJavaScript("[saveCalls,savedSerial,changeSerial]")
        XCTAssertEqual(state as? [Int], [1, 1, 1])

        _ = try await view.evaluateJavaScript("changeSerial++; saveDraftNow=async function(){throw Error('Synthetic save failure')}; true")
        do {
            _ = try await page.saveBeforeNavigation(configuration)
            XCTFail("A failed save must not allow Studio replacement")
        } catch { /* Caller keeps the existing page and offers retry. */ }

        _ = try await view.evaluateJavaScript("saveDraftNow=async function(){savedSerial=changeSerial;mediaUploading=true}; true")
        let busyDuringSave = try await page.saveBeforeNavigation(configuration)
        XCTAssertFalse(busyDuringSave)
        _ = try await view.evaluateJavaScript("mediaUploading=false;changeSerial++;saveDraftNow=async function(){savedSerial=changeSerial;changeSerial++}; true")
        let changedDuringSave = try await page.saveBeforeNavigation(configuration)
        XCTAssertFalse(changedDuringSave)

        // A different configured environment must never evaluate the page's save code.
        let otherOrigin = try ZovaConfiguration(base: URL(string: "https://zova-tiktok-sandbox.onrender.com")!)
        _ = try await view.evaluateJavaScript("saveDraftNow=async function(){throw Error('Must not execute across origins')}; true")
        let unrelated = try await page.saveBeforeNavigation(otherOrigin)
        XCTAssertTrue(unrelated)
        withExtendedLifetime((view, navigation)) { }
    }

    func testInitialPostKeepsNativeHeaderBodyAndRedirectSessionCookie() async throws {
        let ready = expectation(description: "Loopback listener ready")
        let exchanged = expectation(description: "WebKit posted synthetic ticket")
        let opened = expectation(description: "Redirect retained session cookie")
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        listener.stateUpdateHandler = { state in if case .ready = state { ready.fulfill() } }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .main)
            Self.read(connection, buffered: Data(), exchanged: exchanged, opened: opened)
        }
        listener.start(queue: .main)
        defer { listener.cancel() }
        // CI's cold network process has taken >5s before the listener was ready.
        // Keep the handshake assertions strict; allow bounded setup time first.
        await fulfillment(of: [ready], timeout: 30)
        let port = try XCTUnwrap(listener.port?.rawValue)
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let view = WKWebView(frame: CGRect(x: 0, y: 0, width: 390, height: 844), configuration: configuration)
        var request = URLRequest(url: URL(string: "http://127.0.0.1:\(port)/mobile/web-session")!)
        request.httpMethod = "POST"
        request.httpBody = Data("ticket=synthetic-one-use-ticket".utf8)
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.setValue("1", forHTTPHeaderField: "X-Zova-Native-Handoff")
        let navigation = WebKitProbeNavigation()
        view.navigationDelegate = navigation
        view.load(request)
        // A cold CI simulator may need over20s to launch WebKit's processes.
        await fulfillment(of: [exchanged, opened], timeout: 60)
        // Keep WebKit alive until its redirect completes.
        XCTAssertNotNil(view.url)
        withExtendedLifetime(navigation) { }
    }

    func testNativeCookieInstallPrecedesFirstWebKitGET() async throws {
        let ready = expectation(description: "Cookie listener ready")
        let opened = expectation(description: "First GET has installed HttpOnly cookie")
        let parameters = NWParameters.tcp
        parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
        let listener = try NWListener(using: parameters)
        listener.stateUpdateHandler = { if case .ready = $0 { ready.fulfill() } }
        listener.newConnectionHandler = { connection in
            connection.start(queue: .main)
            Self.read(connection, buffered: Data(), exchanged: opened, opened: opened)
        }
        listener.start(queue: .main)
        defer { listener.cancel() }
        await fulfillment(of: [ready], timeout: 30)
        let port = try XCTUnwrap(listener.port?.rawValue)
        let url = URL(string: "http://127.0.0.1:\(port)/studio")!
        let cookie = try XCTUnwrap(HTTPCookie.cookies(withResponseHeaderFields: ["Set-Cookie":"zova_probe=synthetic; Path=/; HttpOnly; SameSite=Lax"], for: url).first)
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        let request = try await StudioBootstrap.request(NativeWebSession(url: url, cookie: cookie), store: configuration.websiteDataStore.httpCookieStore)
        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertNil(request.httpBody)
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        let view = WKWebView(frame: CGRect(x: 0, y: 0, width: 390, height: 844), configuration: configuration)
        let navigation = WebKitProbeNavigation()
        view.navigationDelegate = navigation
        view.load(request)
        await fulfillment(of: [opened], timeout: 60)
        withExtendedLifetime((view, navigation)) { }
    }

    func testProductionCoordinatorRejectsHTTPAndNonHTTPJSONWithoutMarkingReady() throws {
        let page = StudioPage("/studio")
        var ready = false
        let surface = StudioSurface(page: page, configuration: try ZovaConfiguration(base: URL(string: "https://zova-social.com")!), ready: { ready = true }, signedOut: {}, browser: { _ in }, external: { _ in }, share: { _ in })
        let coordinator = surface.makeCoordinator()
        XCTAssertTrue(coordinator.responds(to: NSSelectorFromString("webView:decidePolicyForNavigationResponse:decisionHandler:")))
        let url = URL(string: "https://zova-social.com/mobile/web-session")!
        XCTAssertFalse(coordinator.acceptResponse(HTTPURLResponse(url: url, statusCode: 403, httpVersion: nil, headerFields: ["Content-Type":"application/json"])!))
        XCTAssertNotNil(page.failure)
        XCTAssertFalse(coordinator.acceptResponse(URLResponse(url: url, mimeType: "application/json", expectedContentLength: 0, textEncodingName: "utf-8")))
        XCTAssertFalse(ready)
        XCTAssertTrue(coordinator.acceptResponse(HTTPURLResponse(url: URL(string: "https://zova-social.com/account/export")!, statusCode: 200, httpVersion: nil, headerFields: ["Content-Type":"application/json", "Content-Disposition":"attachment; filename=export.json"])!))
        XCTAssertTrue(coordinator.acceptResponse(HTTPURLResponse(url: URL(string: "https://zova-social.com/studio")!, statusCode: 200, httpVersion: nil, headerFields: ["Content-Type":"text/html"])!))
    }

    nonisolated private static func read(_ connection: NWConnection, buffered: Data,
                             exchanged: XCTestExpectation, opened: XCTestExpectation) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { chunk, _, _, error in
            guard error == nil, let chunk, !chunk.isEmpty else { connection.cancel(); return }
            var data = buffered; data.append(chunk)
            guard let text = String(data: data, encoding: .utf8),
                  let split = text.range(of: "\r\n\r\n") else {
                read(connection, buffered: data, exchanged: exchanged, opened: opened); return
            }
            let head = String(text[..<split.lowerBound]).lowercased()
            let body = String(text[split.upperBound...])
            print("Synthetic WebKit loopback headers: " + head)
            if head.hasPrefix("post /mobile/web-session ") {
                let declared = head.components(separatedBy: "\r\n")
                    .first(where: { $0.hasPrefix("content-length:") })
                    .flatMap { Int($0.dropFirst("content-length:".count).trimmingCharacters(in: .whitespaces)) } ?? 0
                if body.utf8.count < declared {
                    read(connection, buffered: data, exchanged: exchanged, opened: opened); return
                }
                XCTAssertEqual(body, "ticket=synthetic-one-use-ticket")
                XCTAssertTrue(head.contains("x-zova-native-handoff: 1"))
                XCTAssertTrue(head.contains("content-type: application/x-www-form-urlencoded"))
                exchanged.fulfill()
                send(connection, "HTTP/1.1 303 See Other\r\nLocation: /studio\r\nSet-Cookie: zova_probe=synthetic; Path=/; HttpOnly; SameSite=Lax\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            } else if head.hasPrefix("get /studio ") {
                XCTAssertTrue(head.contains("zova_probe=synthetic"))
                opened.fulfill()
                send(connection, "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 15\r\nConnection: close\r\n\r\n<h1>Studio</h1>")
            } else {
                send(connection, "HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            }
        }
    }
    nonisolated private static func send(_ connection: NWConnection, _ text: String) {
        connection.send(content: Data(text.utf8), completion: .contentProcessed { _ in connection.cancel() })
    }
}

@MainActor
private final class WebKitProbeNavigation: NSObject, WKNavigationDelegate {
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        XCTFail("WebKit loopback navigation failed: " + error.localizedDescription)
    }
}

@MainActor
private final class StudioGuardProbeNavigation: NSObject, WKNavigationDelegate {
    let loaded: XCTestExpectation
    init(_ loaded: XCTestExpectation) { self.loaded = loaded }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) { loaded.fulfill() }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        XCTFail("Synthetic Studio document failed: " + error.localizedDescription)
        loaded.fulfill()
    }
}
