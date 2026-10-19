import Foundation

private final class RedirectGuard: NSObject, URLSessionTaskDelegate {
    let configuration: ZovaConfiguration
    init(_ configuration: ZovaConfiguration) { self.configuration = configuration }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        // An API must return JSON directly; never forward credentials on redirects.
        completionHandler(nil)
    }
}

actor NativeAPI {
    let configuration: ZovaConfiguration
    private let session: URLSession
    private var tokens: NativeTokens?
    private var rotation: Task<NativeTokens, Error>?
    init(configuration: ZovaConfiguration) {
        self.configuration = configuration
        let settings = URLSessionConfiguration.ephemeral
        settings.httpCookieStorage = nil
        settings.httpShouldSetCookies = false
        settings.urlCache = nil
        settings.timeoutIntervalForRequest = 30
        settings.timeoutIntervalForResource = 45
        session = URLSession(configuration: settings, delegate: RedirectGuard(configuration), delegateQueue: nil)
    }
    private func request(_ path: String, body: [String: String]? = nil, token: String? = nil) async throws -> Data {
        var request = URLRequest(url: try configuration.endpoint(path))
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpMethod = "POST"
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let token { request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization") }
        let (data, response) = try await session.data(for: request)
        guard let response = response as? HTTPURLResponse else { throw ZovaFailure.invalidResponse }
        if response.statusCode == 401 { throw ZovaFailure.signInRequired }
        if response.statusCode == 429 { throw ZovaFailure.server("Please wait a moment before trying again.") }
        guard (200...299).contains(response.statusCode), data.count <= 1_048_576 else { throw ZovaFailure.unavailable }
        return data
    }
    func ensureAvailable() async throws {
        let data = try await request("/api/v1/native-config")
        struct Config: Decodable { let enabled: Bool; let redirect_uri: String }
        let value = try JSONDecoder().decode(Config.self, from: data)
        guard value.enabled, value.redirect_uri == configuration.callback.absoluteString else {
            throw ZovaFailure.server("The iPhone beta isn’t available on this server yet. Please try again later.")
        }
    }
    func exchange(code: String, verifier: String) async throws {
        let data = try await request("/api/v1/auth/token", body: ["client_id": "zova-ios", "redirect_uri": configuration.callback.absoluteString, "code": code, "code_verifier": verifier])
        let pair = try JSONDecoder().decode(TokenReply.self, from: data).tokens()
        try KeychainVault.save(pair)
        tokens = pair
    }
    private func access() async throws -> String {
        if tokens == nil { tokens = try KeychainVault.load() }
        guard let pair = tokens else { throw ZovaFailure.signInRequired }
        if pair.expires.timeIntervalSinceNow > 45 { return pair.access }
        if let rotation { return try await rotation.value.access }
        let task = Task<NativeTokens, Error> {
            let data = try await self.request("/api/v1/auth/refresh", body: ["refresh_token": pair.refresh])
            let next = try JSONDecoder().decode(TokenReply.self, from: data).tokens()
            try KeychainVault.save(next)
            return next
        }
        rotation = task
        do {
            let next = try await task.value
            tokens = next; rotation = nil
            return next.access
        } catch {
            rotation = nil
            // A lost rotation response is ambiguous; do not replay its old token.
            tokens = nil; try? KeychainVault.clear()
            throw ZovaFailure.signInRequired
        }
    }
    func handoff(destination: String, browser: Bool = false) async throws -> URLRequest {
        let token = try await access()
        let data = try await request("/api/v1/native-handoff", body: ["destination": destination, "purpose": browser ? "browser" : "studio"], token: token)
        struct Reply: Decodable { let ticket: String }
        let value = try JSONDecoder().decode(Reply.self, from: data)
        guard (40...100).contains(value.ticket.count), value.ticket.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "_" || $0 == "-") }) else { throw ZovaFailure.invalidResponse }
        if browser { return URLRequest(url: try configuration.endpoint("/mobile/browser/" + value.ticket)) }
        var result = URLRequest(url: try configuration.endpoint("/mobile/web-session"))
        result.httpMethod = "POST"
        result.httpBody = Data(("ticket=" + value.ticket).utf8)
        result.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        return result
    }
    func logout() async {
        if let pair = tokens ?? (try? KeychainVault.load()) {
            _ = try? await request("/api/v1/auth/logout", body: [:], token: pair.access)
        }
        rotation?.cancel(); rotation = nil; tokens = nil
        try? KeychainVault.clear()
    }
    func forget() { rotation?.cancel(); rotation = nil; tokens = nil; try? KeychainVault.clear() }
}
