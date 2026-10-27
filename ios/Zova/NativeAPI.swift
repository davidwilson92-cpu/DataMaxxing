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
    private var sessionEpoch = 0
    private var productCookie: HTTPCookie?
    private var productSessionTask: Task<NativeWebSession, Error>?
    init(configuration: ZovaConfiguration, transport: URLSessionConfiguration = .ephemeral) {
        self.configuration = configuration
        let settings = transport
        settings.httpCookieStorage = nil
        settings.httpShouldSetCookies = false
        settings.urlCache = nil
        settings.timeoutIntervalForRequest = 30
        settings.timeoutIntervalForResource = 240
        session = URLSession(configuration: settings, delegate: RedirectGuard(configuration), delegateQueue: nil)
    }
    private func request(_ path: String, body: [String: String]? = nil, token: String? = nil) async throws -> Data {
        try await response(path, body: body, token: token).0
    }
    private func response(_ path: String, body: [String: String]? = nil, token: String? = nil) async throws -> (Data, HTTPURLResponse) {
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
        return (data, response)
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
        let epoch = sessionEpoch
        let data = try await request("/api/v1/auth/token", body: ["client_id": "zova-ios", "redirect_uri": configuration.callback.absoluteString, "code": code, "code_verifier": verifier])
        let pair = try JSONDecoder().decode(TokenReply.self, from: data).tokens()
        guard epoch == sessionEpoch else { throw ZovaFailure.signInRequired }
        try KeychainVault.save(pair)
        tokens = pair
    }
    private func access() async throws -> String {
        if tokens == nil { tokens = try KeychainVault.load() }
        guard let pair = tokens else { throw ZovaFailure.signInRequired }
        if pair.expires.timeIntervalSinceNow > 45 { return pair.access }
        let epoch = sessionEpoch
        if let rotation {
            let next = try await rotation.value
            guard epoch == sessionEpoch else { throw ZovaFailure.signInRequired }
            return next.access
        }
        let task = Task<NativeTokens, Error> {
            let data = try await self.request("/api/v1/auth/refresh", body: ["refresh_token": pair.refresh])
            let next = try JSONDecoder().decode(TokenReply.self, from: data).tokens()
            return next
        }
        rotation = task
        do {
            let next = try await task.value
            guard epoch == sessionEpoch else { throw ZovaFailure.signInRequired }
            try KeychainVault.save(next)
            tokens = next; rotation = nil
            return next.access
        } catch {
            guard epoch == sessionEpoch else { throw ZovaFailure.signInRequired }
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
        // The initial WebKit navigation may send Origin:null. A non-simple
        // header distinguishes this ticket exchange from a cross-site form.
        result.setValue("1", forHTTPHeaderField: "X-Zova-Native-Handoff")
        return result
    }
    func webSession(destination: String) async throws -> NativeWebSession {
        let epoch = sessionEpoch
        let token = try await access()
        let data = try await request("/api/v1/native-handoff", body: ["destination": destination, "purpose": "studio"], token: token)
        struct Ticket: Decodable { let ticket: String }
        let ticket = try JSONDecoder().decode(Ticket.self, from: data).ticket
        guard (40...100).contains(ticket.count) else { throw ZovaFailure.invalidResponse }
        let (result, headers) = try await response("/api/v1/native-web-session", body: ["ticket": ticket], token: token)
        struct Target: Decodable { let destination: String }
        let target = try JSONDecoder().decode(Target.self, from: result).destination
        guard epoch == sessionEpoch else { throw ZovaFailure.signInRequired }
        guard target == destination else { throw ZovaFailure.invalidResponse }
        let values = headers.allHeaderFields.reduce(into: [String: String]()) { result, item in
            if let key = item.key as? String, let value = item.value as? String { result[key] = value }
        }
        let cookies = HTTPCookie.cookies(withResponseHeaderFields: values, for: configuration.base)
        guard let cookie = cookies.first(where: { $0.name == "nova_session" }),
              cookie.domain == configuration.base.host, cookie.path == "/",
              cookie.isSecure, cookie.isHTTPOnly, cookie.value.hasPrefix("ios.") else { throw ZovaFailure.invalidResponse }
        return NativeWebSession(url: try configuration.endpoint(target), cookie: cookie)
    }
    func logout() async {
        // Rotate if needed before revoking the device. An expired access token
        // cannot revoke the server session even while its product cookie works.
        let token = try? await access()
        forget()
        if let token {
            _ = try? await request("/api/v1/auth/logout", body: [:], token: token)
        }
    }
    func deviceSessions() async throws -> JSONValue {
        let token = try await access()
        let data = try await request("/api/v1/auth/sessions", token: token)
        return try JSONDecoder().decode(JSONValue.self, from: data)
    }
    func revokeDevice(_ id: String) async throws {
        guard !id.isEmpty, id.allSatisfy({ $0.isASCII && ($0.isLetter || $0.isNumber || $0 == "-" || $0 == "_") }) else { throw ZovaFailure.invalidResponse }
        var request = URLRequest(url: try configuration.endpoint("/api/v1/auth/sessions/" + id))
        request.httpMethod = "DELETE"; request.setValue("Bearer " + (try await access()), forHTTPHeaderField: "Authorization")
        let (_, raw) = try await session.data(for: request)
        guard let response = raw as? HTTPURLResponse, response.statusCode == 204 else { throw ZovaFailure.unavailable }
    }
    func forget() {
        sessionEpoch += 1; rotation?.cancel(); rotation = nil; tokens = nil
        productSessionTask?.cancel(); productSessionTask = nil; productCookie = nil
        try? KeychainVault.clear()
    }

    private func productSession() async throws -> HTTPCookie {
        if let cookie = productCookie, (cookie.expiresDate ?? .distantPast) > Date() { return cookie }
        let epoch = sessionEpoch
        let task: Task<NativeWebSession, Error>
        if let existing = productSessionTask { task = existing }
        else {
            task = Task { try await self.webSession(destination: "/studio") }
            productSessionTask = task
        }
        do {
            let value = try await task.value
            guard epoch == sessionEpoch else { throw ZovaFailure.signInRequired }
            productCookie = value.cookie; productSessionTask = nil
            return value.cookie
        } catch { if epoch == sessionEpoch { productSessionTask = nil }; throw error }
    }

    /// Product requests use existing guarded endpoints, with no HTML renderer,
    /// redirects, persistent cookie jar, disk cache or automatic mutation replay.
    func product(_ path: String, method: String = "GET", body: JSONValue? = nil, brand: Int = 0) async throws -> JSONValue {
        let data = try body?.encoded()
        let result = try await productResponse(path, method: method, data: data, contentType: "application/json", brand: brand)
        if result.0.isEmpty { return .null }
        return try JSONDecoder().decode(JSONValue.self, from: result.0)
    }

    func form(_ path: String, fields: [String: String], brand: Int = 0) async throws -> JSONValue {
        let encoded = fields.sorted { $0.key < $1.key }.map { ProductLinks.query($0.key) + "=" + ProductLinks.query($0.value) }.joined(separator: "&")
        let (data, response) = try await productResponse(path, method: "POST", data: Data(encoded.utf8), contentType: "application/x-www-form-urlencoded", brand: brand, allowFormRedirect: true)
        if let target = response.value(forHTTPHeaderField: "Location") {
            let url = try configuration.endpoint(target)
            let parts = URLComponents(url: url, resolvingAgainstBaseURL: false)
            if let error = parts?.queryItems?.first(where: { $0.name == "error" })?.value {
                let message = ["profile": "Enter your name.", "current_password": "The current password is incorrect.", "password_length": "Use 10–256 characters.", "password_match": "The new passwords do not match."][error] ?? "That change could not be saved. Check the details and try again."
                throw ProductError(status: 400, code: error, message: message)
            }
            return .object(["destination": .string(target)])
        }
        return data.isEmpty ? .null : try JSONDecoder().decode(JSONValue.self, from: data)
    }

    func upload(file: URL, name: String, mime: String, brand: Int) async throws -> JSONValue {
        let boundary = "Zova-" + UUID().uuidString
        let body = try NativeMediaFiles.multipart(file: file, filename: name, mime: mime, boundary: boundary)
        defer { NativeMediaFiles.remove(body) }
        let (request, epoch) = try await productRequest("/api/media", method: "POST", contentType: "multipart/form-data; boundary=\(boundary)", brand: brand)
        let (result, raw) = try await session.upload(for: request, fromFile: body)
        _ = try validateProduct(result, raw: raw, epoch: epoch)
        return try JSONDecoder().decode(JSONValue.self, from: result)
    }

    func downloadAsset(_ id: Int, filename: String, brand: Int) async throws -> URL {
        guard id > 0 else { throw ZovaFailure.unsafeURL }
        // This authenticated endpoint streams owned media; preview redirects are
        // intentionally avoided so a social/media host never receives credentials.
        let (request, epoch) = try await productRequest("/media/download/\(id)", method: "GET", contentType: nil, brand: brand)
        let (download, raw) = try await session.download(for: request)
        defer { try? FileManager.default.removeItem(at: download) }
        guard epoch == sessionEpoch else { throw ZovaFailure.signInRequired }
        guard let response = raw as? HTTPURLResponse else { throw ZovaFailure.invalidResponse }
        if response.statusCode == 401 { productCookie = nil; throw ZovaFailure.signInRequired }
        guard response.statusCode == 200,
              let size = try FileManager.default.attributesOfItem(atPath: download.path)[.size] as? NSNumber,
              size.intValue > 0, size.intValue <= 160 * 1024 * 1024 else { throw ZovaFailure.unavailable }
        let destination = try NativeMediaFiles.create(extension: (filename as NSString).pathExtension)
        do {
            try FileManager.default.removeItem(at: destination)
            try FileManager.default.moveItem(at: download, to: destination)
            try FileManager.default.setAttributes([.protectionKey: FileProtectionType.complete], ofItemAtPath: destination.path)
            return destination
        } catch { NativeMediaFiles.remove(destination); throw error }
    }

    private func productRequest(_ path: String, method: String, contentType: String?, brand: Int) async throws -> (URLRequest, Int) {
        let epoch = sessionEpoch
        let cookie = try await productSession()
        guard epoch == sessionEpoch, brand >= 0 else { throw ZovaFailure.signInRequired }
        var request = URLRequest(url: try configuration.endpoint(path))
        request.httpMethod = method
        request.timeoutInterval = 180; request.cachePolicy = .reloadIgnoringLocalCacheData
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(cookie.name + "=" + cookie.value, forHTTPHeaderField: "Cookie")
        request.setValue(configuration.base.absoluteString.trimmingCharacters(in: CharacterSet(charactersIn: "/")), forHTTPHeaderField: "Origin")
        request.setValue(String(brand), forHTTPHeaderField: "X-Zova-Brand")
        if let contentType { request.setValue(contentType, forHTTPHeaderField: "Content-Type") }
        return (request, epoch)
    }
    private func productResponse(_ path: String, method: String, data: Data?, contentType: String?, brand: Int,
                                 allowFormRedirect: Bool = false) async throws -> (Data, HTTPURLResponse) {
        var (request, epoch) = try await productRequest(path, method: method, contentType: contentType, brand: brand)
        request.httpBody = data
        let (result, raw) = try await session.data(for: request)
        return (result, try validateProduct(result, raw: raw, epoch: epoch, allowFormRedirect: allowFormRedirect))
    }
    private func validateProduct(_ result: Data, raw: URLResponse, epoch: Int, allowFormRedirect: Bool = false) throws -> HTTPURLResponse {
        guard epoch == sessionEpoch else { throw ZovaFailure.signInRequired }
        guard let response = raw as? HTTPURLResponse else { throw ZovaFailure.invalidResponse }
        if response.statusCode == 401 { productCookie = nil; throw ZovaFailure.signInRequired }
        if response.statusCode == 303, allowFormRedirect { return response }
        guard (200...299).contains(response.statusCode) else {
            let value = (try? JSONDecoder().decode(JSONValue.self, from: result)) ?? .null
            let text = value["detail"].string
            throw ProductError(status: response.statusCode, code: value["code"].string,
                               message: text.isEmpty ? "Zova couldn’t complete that request. Your saved work is unchanged." : String(text.prefix(800)))
        }
        guard result.count <= 4 * 1024 * 1024 else { throw ZovaFailure.invalidResponse }
        return response
    }
}

struct NativeWebSession {
    let url: URL
    let cookie: HTTPCookie
}
