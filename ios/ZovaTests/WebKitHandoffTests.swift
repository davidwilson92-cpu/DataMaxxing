import XCTest
import WebKit
import Network
@testable import Zova

// Exercise WebKit's actual network process, not just URLSession mocks. The
// listener is loopback-only and uses disposable synthetic credentials.
@MainActor
final class WebKitHandoffTests: XCTestCase {
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
        await fulfillment(of: [ready], timeout: 5)
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
        await fulfillment(of: [ready], timeout: 5)
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
