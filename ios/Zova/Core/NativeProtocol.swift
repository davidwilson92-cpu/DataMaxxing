import Foundation
import CryptoKit
import Security

enum ZovaFailure: LocalizedError {
    case signInRequired, cancelled, unsafeURL, invalidCallback, unavailable, invalidResponse, secureStorage
    case server(String)
    var errorDescription: String? {
        switch self {
        case .signInRequired: return "Please sign in to continue. Your saved work is on your account."
        case .cancelled: return "Sign-in cancelled. You can try again when you’re ready."
        case .unsafeURL: return "This link can’t be opened inside Zova."
        case .invalidCallback: return "This sign-in request expired. Please start again."
        case .unavailable: return "Zova can’t connect right now. Check your connection and try again."
        case .invalidResponse: return "Zova couldn’t confirm the response. Please try again."
        case .secureStorage: return "Zova couldn’t securely save your sign-in. Please try again."
        case .server(let message): return message
        }
    }
}

struct ZovaConfiguration {
    let base: URL
    var callback: URL { base.appendingPathComponent("mobile/callback") }
    init(base: URL) throws {
        guard base.scheme == "https", base.user == nil, base.password == nil,
              base.port == nil, base.query == nil, base.fragment == nil,
              ["zova-social.com", "zova-tiktok-sandbox.onrender.com"].contains(base.host?.lowercased() ?? ""),
              base.path.isEmpty || base.path == "/" else { throw ZovaFailure.unsafeURL }
        self.base = base
    }
    static var bundled: ZovaConfiguration {
        // Configuration is build-time, not an editable server address or a secret.
        let value = Bundle.main.object(forInfoDictionaryKey: "ZovaServerURL") as? String ?? "https://zova-social.com"
        return try! ZovaConfiguration(base: URL(string: value)!)
    }
    func owns(_ url: URL) -> Bool {
        url.scheme == "https" && url.host?.lowercased() == base.host?.lowercased()
            && url.port == nil && url.user == nil && url.password == nil
    }
    func endpoint(_ path: String) throws -> URL {
        guard path.hasPrefix("/"), !path.hasPrefix("//"), !path.contains("\\"),
              let url = URL(string: path, relativeTo: base)?.absoluteURL, owns(url) else { throw ZovaFailure.unsafeURL }
        return url
    }
    func browserDestination(_ url: URL) -> String? {
        guard owns(url) else { return nil }
        let components = URLComponents(url: url, resolvingAgainstBaseURL: false)
        let workspace = components?.queryItems?.first(where: { $0.name == "workspace" })?.value
        var target: String
        if url.path.hasPrefix("/connect/") { target = url.path }
        else if url.path.hasPrefix("/oauth/") {
            if url.path.contains("instagram") { target = "/connect/instagram" }
            else if url.path.contains("meta") { target = "/connect/facebook" }
            else if url.path.contains("tiktok") { target = "/connect/tiktok" }
            else if url.path.contains("/x/") { target = "/connect/x" }
            else { return nil }
        } else { return nil }
        guard ["/connect/instagram", "/connect/facebook", "/connect/tiktok", "/connect/x"].contains(target) else { return nil }
        if let workspace, workspace.allSatisfy(\.isNumber), !workspace.isEmpty { target += "?workspace=" + workspace }
        return target
    }
}

enum NativeProof {
    static func random(_ count: Int = 32) throws -> String {
        var bytes = [UInt8](repeating: 0, count: count)
        guard SecRandomCopyBytes(kSecRandomDefault, count, &bytes) == errSecSuccess else { throw ZovaFailure.secureStorage }
        return base64URL(Data(bytes))
    }
    static func base64URL(_ data: Data) -> String {
        data.base64EncodedString().replacingOccurrences(of: "+", with: "-").replacingOccurrences(of: "/", with: "_").replacingOccurrences(of: "=", with: "")
    }
    static func challenge(_ verifier: String) -> String { base64URL(Data(SHA256.hash(data: Data(verifier.utf8)))) }
    static func equal(_ first: String, _ second: String) -> Bool {
        let a = Array(first.utf8), b = Array(second.utf8)
        guard a.count == b.count else { return false }
        return zip(a, b).reduce(UInt8(0)) { $0 | ($1.0 ^ $1.1) } == 0
    }
    static func code(from url: URL, configuration: ZovaConfiguration, state: String) throws -> String {
        guard configuration.owns(url), url.path == configuration.callback.path, url.fragment == nil,
              let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems,
              items.count == 2,
              let returnedState = items.first(where: { $0.name == "state" })?.value,
              equal(state, returnedState) else { throw ZovaFailure.invalidCallback }
        if Set(items.map(\.name)) == Set(["error", "state"]), items.first(where: { $0.name == "error" })?.value == "access_denied" {
            throw ZovaFailure.cancelled
        }
        guard Set(items.map(\.name)) == Set(["code", "state"]), let code = items.first(where: { $0.name == "code" })?.value,
              (40...100).contains(code.count), code.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "_" || $0 == "-") })
        else { throw ZovaFailure.invalidCallback }
        return code
    }
}

struct NativeTokens: Codable {
    var access: String
    var refresh: String
    var expires: Date
}

struct TokenReply: Decodable {
    let accessToken: String
    let refreshToken: String
    let expiresIn: Double
    enum CodingKeys: String, CodingKey { case accessToken = "access_token", refreshToken = "refresh_token", expiresIn = "expires_in" }
    func tokens() throws -> NativeTokens {
        guard (40...100).contains(accessToken.count), (40...100).contains(refreshToken.count),
              expiresIn > 0, expiresIn <= 3600 else { throw ZovaFailure.invalidResponse }
        return NativeTokens(access: accessToken, refresh: refreshToken, expires: Date().addingTimeInterval(expiresIn))
    }
}
