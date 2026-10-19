import XCTest
@testable import Zova

final class NativeProtocolTests: XCTestCase {
    func testOnlyOwnedHTTPSConfiguration() throws {
        for value in ["http://zova-social.com", "https://zova-social.com.evil.test", "https://user:pass@zova-social.com", "https://zova-social.com:443", "https://zova-social.com?token=secret", "https://zova-social.com/other"] {
            XCTAssertThrowsError(try ZovaConfiguration(base: URL(string: value)!))
        }
        XCTAssertNoThrow(try ZovaConfiguration(base: URL(string: "https://zova-social.com")!))
    }
    func testS256StandardVector() {
        XCTAssertEqual(NativeProof.challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"), "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
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
}
