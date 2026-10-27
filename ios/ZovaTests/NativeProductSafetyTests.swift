import XCTest
@testable import Zova

@MainActor
final class NativeProductSafetyTests: XCTestCase {
    override func tearDown() { try? KeychainVault.clear(); NativeDraftRecovery.remove(owner: "1:0"); NativeMediaFiles.clear() }
    private func api() throws -> NativeAPI {
        NativeProductFixtures.reset(); NativeDraftRecovery.remove(owner: "1:0")
        try KeychainVault.save(NativeTokens(access: String(repeating: "a", count: 64), refresh: String(repeating: "r", count: 64), expires: Date().addingTimeInterval(900)))
        let configuration = URLSessionConfiguration.ephemeral; configuration.protocolClasses = [ProductTestTransport.self]
        ProductTestTransport.respond = { request in
            let (status, value, headers) = NativeProductFixtures.response(request)
            return (status, try! value.encoded(), headers, 0)
        }
        return NativeAPI(configuration: .bundled, transport: configuration)
    }
    func testProductRequestsKeepDeviceTokensOutOfCookieTransport() async throws {
        let api = try api()
        let expected = expectation(description: "owned product request")
        ProductTestTransport.respond = { request in
            if request.url?.path == "/api/native/account" {
                XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
                XCTAssertEqual(request.value(forHTTPHeaderField: "Cookie"), "nova_session=ios.synthetic-fixture")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Origin"), "https://zova-social.com")
                XCTAssertEqual(request.value(forHTTPHeaderField: "X-Zova-Brand"), "12")
                XCTAssertEqual(request.url?.host, "zova-social.com")
                expected.fulfill()
            }
            let (status, value, headers) = NativeProductFixtures.response(request)
            return (status, try! value.encoded(), headers, 0)
        }
        _ = try await api.product("/api/native/account", brand: 12)
        await fulfillment(of: [expected], timeout: 3)
        do { _ = try await api.product("https://untrusted.example/steal"); XCTFail("External request accepted") }
        catch ZovaFailure.unsafeURL { }
    }
    func testServerFailureDoesNotReplayPublish() async throws {
        let api = try api(); let once = expectation(description: "one publication attempt"); once.assertForOverFulfill = true
        ProductTestTransport.respond = { request in
            if request.url?.path == "/api/publish" { once.fulfill(); return (502, Data("{}".utf8), [:], 0) }
            let (status, value, headers) = NativeProductFixtures.response(request); return (status, try! value.encoded(), headers, 0)
        }
        do { _ = try await api.product("/api/publish", method: "POST", body: .object(["review_token": .string("synthetic")])) ; XCTFail("Expected failure") }
        catch let issue as ProductError { XCTAssertEqual(issue.status, 502) }
        await fulfillment(of: [once], timeout: 3)
    }
    func testLateProductResponseCannotRepopulateSignedOutAccount() async throws {
        let api = try api(), store = ProductStore(api: api), started = expectation(description: "account requested")
        ProductTestTransport.respond = { request in
            let (status, value, headers) = NativeProductFixtures.response(request)
            if request.url?.path == "/api/native/account" { started.fulfill(); return (status, try! value.encoded(), headers, 0.2) }
            return (status, try! value.encoded(), headers, 0)
        }
        let pending = Task { try await store.reloadAccount() }
        await fulfillment(of: [started], timeout: 3)
        store.clear(); await api.forget()
        do { try await pending.value; XCTFail("Stale account accepted") } catch { }
        XCTAssertTrue(store.account.isNull); XCTAssertNil(try KeychainVault.load())
    }
    func testFailedSaveBlocksNavigationAndRetainsRecovery() async throws {
        let api = try api(), store = ProductStore(api: api)
        try await store.start(); try await store.openDraft(24)
        store.draft.composer = "Keep this idea"; store.changed()
        ProductTestTransport.respond = { request in
            if request.httpMethod == "PATCH" { return (409, Data("{\"detail\":\"Draft changed elsewhere\"}".utf8), [:], 0) }
            let (status, value, headers) = NativeProductFixtures.response(request); return (status, try! value.encoded(), headers, 0)
        }
        do { try await store.newPost(); XCTFail("Navigation must stop on conflict") } catch { }
        XCTAssertEqual(store.draft.id, 24); XCTAssertEqual(store.draft.composer, "Keep this idea")
        XCTAssertEqual(NativeDraftRecovery.load(owner: "1:0")["workspace"]["composer"].string, "Keep this idea")
        store.clear()
    }
    func testSendingPersistsTranscriptAndEditableCaptionWithoutPublication() async throws {
        let api = try api(), store = ProductStore(api: api)
        try await store.start(); store.draft.composer = "A useful pottery tip"; store.changed()
        await store.perform { try await store.send() }
        XCTAssertNil(store.error); XCTAssertTrue(store.draft.composer.isEmpty)
        XCTAssertEqual(store.draft.conversation.first?["content"].string, "A useful pottery tip")
        XCTAssertFalse(store.caption("instagram").isEmpty); XCTAssertTrue(store.draft.editable)
        let id = try XCTUnwrap(store.draft.id); try await store.openDraft(id)
        XCTAssertFalse(store.caption("instagram").isEmpty); XCTAssertTrue(store.draft.composer.isEmpty)
        store.clear()
    }
    func testRecoveryCannotOverwriteChangedServerDraft() async throws {
        let api = try api(), store = ProductStore(api: api)
        try await store.start()
        var old = ProductDraft(NativeProductFixtures.draft(24)); old.revision = 0; old.composer = "Recover separately"
        try NativeDraftRecovery.save(old, owner: "1:0"); store.recovery = NativeDraftRecovery.load(owner: "1:0")
        do { try await store.restoreRecovery(); XCTFail("Stale recovery must not overwrite") } catch { }
        XCTAssertFalse(store.recovery.isNull)
        try await store.restoreRecovery(asNew: true)
        XCTAssertNotEqual(store.draft.id, 24); XCTAssertEqual(store.draft.composer, "Recover separately")
        XCTAssertTrue(NativeDraftRecovery.load(owner: "another-user:0").isNull)
        store.clear()
    }
    func testFileBackedMultipartAndCleanupCannotDeleteUnownedFile() throws {
        let source = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".mp4")
        let original = Data(repeating: 17, count: 130_000); try original.write(to: source)
        defer { try? FileManager.default.removeItem(at: source) }
        let body = try NativeMediaFiles.multipart(file: source, filename: "clip\"\r\n.mp4", mime: "video/mp4", boundary: "test-boundary")
        let data = try Data(contentsOf: body)
        XCTAssertNotNil(data.range(of: original)); XCTAssertTrue(String(decoding: data.prefix(150), as: UTF8.self).contains("filename=\"clip.mp4\""))
        NativeMediaFiles.remove(source); XCTAssertTrue(FileManager.default.fileExists(atPath: source.path))
        NativeMediaFiles.remove(body); XCTAssertFalse(FileManager.default.fileExists(atPath: body.path))
    }
}

private final class ProductTestTransport: URLProtocol {
    static var respond: ((URLRequest) -> (Int, Data, [String: String], Double))!
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        let (status, bytes, headers, delay) = Self.respond(request)
        DispatchQueue.global().asyncAfter(deadline: .now() + delay) { [self] in
            client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: ["Content-Type":"application/json"].merging(headers) { _, new in new })!, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: bytes); client?.urlProtocolDidFinishLoading(self)
        }
    }
    override func stopLoading() { }
}
