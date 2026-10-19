import XCTest
@testable import Zova

final class NativeProtocolTests: XCTestCase {
    func testInstagramUsesNormalBrowserWithoutChangingOtherProviderRoutes() throws {
        let configuration = try ZovaConfiguration(base: URL(string: "https://zova-social.com")!)
        XCTAssertTrue(configuration.usesSystemBrowser(for: "/connect/instagram?workspace=8"))
        for value in ["/connect/facebook", "/connect/tiktok", "/connect/x", "/connect/instagram/other", "https://evil.test/connect/instagram", "//evil.test/connect/instagram"] {
            XCTAssertFalse(configuration.usesSystemBrowser(for: value))
        }
        let link = URL(string: "https://zova-social.com/oauth/instagram/facebook/start?workspace=8")!
        XCTAssertEqual(configuration.browserDestination(link), "/connect/instagram?workspace=8")
    }
    func testOnlyOwnedHTTPSConfiguration() throws {
        for value in ["http://zova-social.com", "https://zova-social.com.evil.test", "https://user:pass@zova-social.com", "https://zova-social.com:443", "https://zova-social.com?token=secret", "https://zova-social.com/other"] {
            XCTAssertThrowsError(try ZovaConfiguration(base: URL(string: value)!))
        }
        XCTAssertNoThrow(try ZovaConfiguration(base: URL(string: "https://zova-social.com")!))
    }
    func testS256StandardVector() {
        XCTAssertEqual(NativeProof.challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"), "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
    }
    func testCancellationRequiresTheSameOwnedCallbackAndState() throws {
        let configuration = try ZovaConfiguration(base: URL(string: "https://zova-social.com")!)
        let state = String(repeating: "s", count: 43)
        do {
            _ = try NativeProof.code(from: URL(string: "https://zova-social.com/mobile/callback?error=access_denied&state=\(state)")!, configuration: configuration, state: state)
            XCTFail("Expected cancellation")
        } catch ZovaFailure.cancelled { }
        for value in [
            "https://zova-social.com/mobile/callback?error=access_denied&state=wrong",
            "https://evil.test/mobile/callback?error=access_denied&state=\(state)",
            "https://zova-social.com/mobile/callback?error=other&state=\(state)"
        ] {
            do { _ = try NativeProof.code(from: URL(string: value)!, configuration: configuration, state: state); XCTFail("Expected invalid callback") }
            catch ZovaFailure.invalidCallback { }
        }
    }
    func testCallbackChecksStateHostPathAndDuplicates() throws {
        let configuration = try ZovaConfiguration(base: URL(string: "https://zova-social.com")!)
        let code = String(repeating: "c", count: 43), state = String(repeating: "s", count: 43)
        XCTAssertEqual(try NativeProof.code(from: URL(string: "https://zova-social.com/mobile/callback?code=\(code)&state=\(state)")!, configuration: configuration, state: state), code)
        for value in [
            "https://zova-social.com/mobile/callback?code=\(code)&state=other",
            "https://evil.test/mobile/callback?code=\(code)&state=\(state)",
            "https://zova-social.com/other?code=\(code)&state=\(state)",
            "https://zova-social.com/mobile/callback?code=\(code)&state=\(state)&state=\(state)",
            "https://zova-social.com/mobile/callback?code=short&state=\(state)",
            "https://zova-social.com/mobile/callback?code=\(code)&state=\(state)#extra"
        ] { XCTAssertThrowsError(try NativeProof.code(from: URL(string: value)!, configuration: configuration, state: state)) }
    }
    func testExternalURLsCannotReceiveOwnedRequests() throws {
        let configuration = try ZovaConfiguration(base: URL(string: "https://zova-social.com")!)
        for path in ["//evil.test", "https://evil.test", "/\\evil.test"] { XCTAssertThrowsError(try configuration.endpoint(path)) }
        XCTAssertEqual(try configuration.endpoint("/studio?draft=4").host, "zova-social.com")
    }
    func testSocialConnectionsUseBrowserWithoutChangingWorkspace() throws {
        let configuration = try ZovaConfiguration(base: URL(string: "https://zova-social.com")!)
        XCTAssertEqual(configuration.browserDestination(URL(string: "https://zova-social.com/oauth/instagram/facebook/start?workspace=12")!), "/connect/instagram?workspace=12")
        XCTAssertEqual(configuration.browserDestination(URL(string: "https://zova-social.com/oauth/meta/start?workspace=3")!), "/connect/facebook?workspace=3")
        XCTAssertNil(configuration.browserDestination(URL(string: "https://evil.test/connect/tiktok")!))
        XCTAssertNil(configuration.browserDestination(URL(string: "https://zova-social.com/other")!))
    }
    func testRandomProofsAreDistinctAndValid() throws {
        let first = try NativeProof.random(), second = try NativeProof.random()
        XCTAssertEqual(first.count, 43)
        XCTAssertNotEqual(first, second)
        XCTAssertFalse(first.contains("="))
        XCTAssertTrue(NativeProof.equal(first, first))
        XCTAssertFalse(NativeProof.equal(first, second))
    }
    func testKeychainRoundtripAndClear() throws {
        try KeychainVault.clear()
        let pair = NativeTokens(access: String(repeating: "a", count: 64), refresh: String(repeating: "r", count: 64), expires: Date().addingTimeInterval(900))
        try KeychainVault.save(pair)
        XCTAssertEqual(try KeychainVault.load()?.access, pair.access)
        try KeychainVault.clear()
        XCTAssertNil(try KeychainVault.load())
    }

    func testLateSignInCannotRestoreForgottenSession() async throws {
        try KeychainVault.clear()
        let started = expectation(description: "Token request started")
        MockNativeTransport.respond = { request in
            XCTAssertEqual(request.url?.host, "zova-social.com")
            XCTAssertEqual(request.url?.path, "/api/v1/auth/token")
            started.fulfill()
            return (200, Self.tokenData, 0.25)
        }
        let api = try mockAPI()
        let pending = Task { try await api.exchange(code: String(repeating: "c", count: 43), verifier: String(repeating: "v", count: 64)) }
        await fulfillment(of: [started], timeout: 3)
        await api.forget()
        do { try await pending.value; XCTFail("Late sign-in must be rejected") }
        catch ZovaFailure.signInRequired { }
        XCTAssertNil(try KeychainVault.load())
    }

    func testConcurrentRefreshUsesOneRotationAndKeepsTokensOutOfWebRequest() async throws {
        try KeychainVault.save(NativeTokens(access: String(repeating: "a", count: 64), refresh: String(repeating: "r", count: 64), expires: .distantPast))
        let refresh = expectation(description: "Single refresh")
        refresh.assertForOverFulfill = true
        MockNativeTransport.respond = { request in
            XCTAssertEqual(request.url?.host, "zova-social.com")
            if request.url?.path == "/api/v1/auth/refresh" {
                refresh.fulfill()
                return (200, Self.tokenData, 0.15)
            }
            XCTAssertEqual(request.url?.path, "/api/v1/native-handoff")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer " + String(repeating: "b", count: 64))
            return (200, Data(("{\"ticket\":\"" + String(repeating: "t", count: 43) + "\"}").utf8), 0)
        }
        let api = try mockAPI()
        async let first = api.handoff(destination: "/studio")
        async let second = api.handoff(destination: "/drafts")
        let values = try await [first, second]
        await fulfillment(of: [refresh], timeout: 3)
        for value in values {
            XCTAssertNil(value.value(forHTTPHeaderField: "Authorization"))
            XCTAssertFalse(value.url!.absoluteString.contains(String(repeating: "b", count: 64)))
            XCTAssertEqual(value.value(forHTTPHeaderField: "X-Zova-Native-Handoff"), "1")
            XCTAssertEqual(value.value(forHTTPHeaderField: "Content-Type"), "application/x-www-form-urlencoded")
            XCTAssertEqual(value.httpMethod, "POST")
            XCTAssertEqual(value.url?.path, "/mobile/web-session")
        }
        XCTAssertEqual(try KeychainVault.load()?.refresh, String(repeating: "n", count: 64))
        await api.forget()
    }

    func testLateRefreshCannotRestoreForgottenSession() async throws {
        try KeychainVault.save(NativeTokens(access: String(repeating: "a", count: 64), refresh: String(repeating: "r", count: 64), expires: .distantPast))
        let started = expectation(description: "Refresh started")
        MockNativeTransport.respond = { request in
            XCTAssertEqual(request.url?.path, "/api/v1/auth/refresh")
            started.fulfill()
            return (200, Self.tokenData, 0.25)
        }
        let api = try mockAPI()
        let pending = Task { try await api.handoff(destination: "/studio") }
        await fulfillment(of: [started], timeout: 3)
        await api.forget()
        do { _ = try await pending.value; XCTFail("Late refresh must be rejected") }
        catch ZovaFailure.signInRequired { }
        XCTAssertNil(try KeychainVault.load())
    }

    func testNativeBootstrapRedeemsOutsideWebKitAndReturnsOnlyCookieAndGETTarget() async throws {
        try KeychainVault.save(NativeTokens(access: String(repeating: "a", count: 64), refresh: String(repeating: "r", count: 64), expires: Date().addingTimeInterval(900)))
        defer { try? KeychainVault.clear() }
        MockNativeTransport.respond = { request in
            XCTAssertNotNil(request.value(forHTTPHeaderField: "Authorization"))
            XCTAssertNil(request.value(forHTTPHeaderField: "Cookie"))
            if request.url?.path == "/api/v1/native-handoff" {
                return (200, Data(("{\"ticket\":\"" + String(repeating: "t", count: 64) + "\"}").utf8), 0)
            }
            XCTAssertEqual(request.url?.path, "/api/v1/native-web-session")
            var body = request.httpBody ?? Data()
            if let stream = request.httpBodyStream {
                stream.open()
                defer { stream.close() }
                var buffer = [UInt8](repeating: 0, count: 1024)
                while stream.hasBytesAvailable {
                    let count = stream.read(&buffer, maxLength: buffer.count)
                    if count <= 0 { break }
                    body.append(contentsOf: buffer.prefix(count))
                }
            }
            let payload = (try? JSONSerialization.jsonObject(with: body)) as? [String: String]
            XCTAssertEqual(payload?["ticket"], String(repeating: "t", count: 64))
            return (200, Data("{\"destination\":\"/studio\"}".utf8), 0)
        }
        let api = try mockAPI()
        let value = try await api.webSession(destination: "/studio")
        XCTAssertEqual(value.url.absoluteString, "https://zova-social.com/studio")
        XCTAssertTrue(value.cookie.isHTTPOnly)
        XCTAssertTrue(value.cookie.isSecure)
        XCTAssertEqual(value.cookie.name, "nova_session")
        await api.forget()
    }

    private static var tokenData: Data { Data(("{\"access_token\":\"" + String(repeating: "b", count: 64) + "\",\"refresh_token\":\"" + String(repeating: "n", count: 64) + "\",\"expires_in\":900}").utf8) }
    private func mockAPI() throws -> NativeAPI {
        let transport = URLSessionConfiguration.ephemeral
        transport.protocolClasses = [MockNativeTransport.self]
        return NativeAPI(configuration: try ZovaConfiguration(base: URL(string: "https://zova-social.com")!), transport: transport)
    }
}

private final class MockNativeTransport: URLProtocol {
    static var respond: ((URLRequest) -> (Int, Data, Double))!
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        let (status, data, delay) = Self.respond(request)
        DispatchQueue.global().asyncAfter(deadline: .now() + delay) { [self] in
            var headers = ["Content-Type": "application/json"]
            if request.url?.path == "/api/v1/native-web-session" {
                headers["Set-Cookie"] = "nova_session=ios.synthetic.bound; Path=/; Max-Age=900; Secure; HttpOnly; SameSite=Lax"
            }
            client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: headers)!, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        }
    }
    override func stopLoading() { }
}
