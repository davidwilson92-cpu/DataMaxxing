import Foundation
import WebKit

/// One-time cleanup of the previous beta's embedded-browser cookies and cache.
/// Product screens never create a WKWebView. Existing Keychain sign-in survives.
@MainActor
enum NativeUpgrade {
    static func clearLegacyWebDataIfNeeded() async {
        guard !UserDefaults.standard.bool(forKey: "zova-native-product-v1") else { return }
        await clear(store: .default())
        UserDefaults.standard.set(true, forKey: "zova-native-product-v1")
    }
    static func clear(store: WKWebsiteDataStore) async {
        await withCheckedContinuation { continuation in
            store.removeData(ofTypes: WKWebsiteDataStore.allWebsiteDataTypes(), modifiedSince: .distantPast) { continuation.resume() }
        }
    }
}
