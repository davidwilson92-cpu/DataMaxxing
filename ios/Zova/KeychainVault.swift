import Foundation
import Security

enum KeychainVault {
    private static var service: String { (Bundle.main.bundleIdentifier ?? "com.zovasocial.app") + ".native-session" }
    private static var query: [String: Any] { [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service, kSecAttrAccount as String: "device"] }
    static func load() throws -> NativeTokens? {
        var request = query
        request[kSecReturnData as String] = true
        request[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(request as CFDictionary, &result)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = result as? Data else { throw ZovaFailure.secureStorage }
        do { return try JSONDecoder().decode(NativeTokens.self, from: data) }
        catch { try? clear(); throw ZovaFailure.signInRequired }
    }
    static func save(_ tokens: NativeTokens) throws {
        let data = try JSONEncoder().encode(tokens)
        let attributes = [kSecValueData as String: data]
        let updated = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if updated == errSecSuccess { return }
        guard updated == errSecItemNotFound else { throw ZovaFailure.secureStorage }
        var item = query
        item[kSecValueData as String] = data
        item[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        item[kSecAttrSynchronizable as String] = false
        guard SecItemAdd(item as CFDictionary, nil) == errSecSuccess else { throw ZovaFailure.secureStorage }
    }
    static func clear() throws {
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else { throw ZovaFailure.secureStorage }
    }
}
