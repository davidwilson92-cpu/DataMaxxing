import XCTest
import WebKit
@testable import Zova

@MainActor
final class NativeUpgradeTests: XCTestCase {
    func testUpgradeRemovesOldBrowserCookieWithoutClearingNativeCredentials() async throws {
        let store = WKWebsiteDataStore.nonPersistent()
        let cookie = try XCTUnwrap(HTTPCookie(properties: [.domain: "zova-social.com", .path: "/", .name: "nova_session", .value: "synthetic-old-beta", .secure: "TRUE"]))
        await store.httpCookieStore.setCookie(cookie)
        let before = await store.httpCookieStore.allCookies()
        XCTAssertEqual(before.count, 1)
        let pair = NativeTokens(access: "synthetic-native", refresh: "synthetic-refresh", expires: Date().addingTimeInterval(600))
        try KeychainVault.save(pair)
        defer { try? KeychainVault.clear() }
        await NativeUpgrade.clear(store: store)
        let after = await store.httpCookieStore.allCookies()
        XCTAssertTrue(after.isEmpty)
        XCTAssertEqual(try KeychainVault.load()?.access, pair.access)
    }
}
