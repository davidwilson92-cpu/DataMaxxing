import AuthenticationServices
import UIKit

@MainActor
final class NativeSignIn: NSObject, ASWebAuthenticationPresentationContextProviding {
    private var session: ASWebAuthenticationSession?
    private var continuation: CheckedContinuation<URL, Error>?
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows).first(where: \.isKeyWindow) ?? ASPresentationAnchor()
    }
    func open(configuration: ZovaConfiguration, challenge: String, state: String) async throws -> URL {
        guard session == nil else { throw ZovaFailure.server("Sign-in is already open.") }
        var parts = URLComponents(url: try configuration.endpoint("/mobile/authorize"), resolvingAgainstBaseURL: false)!
        parts.queryItems = [URLQueryItem(name: "client_id", value: "zova-ios"), URLQueryItem(name: "redirect_uri", value: configuration.callback.absoluteString), URLQueryItem(name: "code_challenge", value: challenge), URLQueryItem(name: "code_challenge_method", value: "S256"), URLQueryItem(name: "state", value: state)]
        return try await withCheckedThrowingContinuation { continuation in
            self.continuation = continuation
            let flow = ASWebAuthenticationSession(url: parts.url!, callback: .https(host: configuration.base.host!, path: configuration.callback.path)) { [weak self] url, error in
                Task { @MainActor in
                    guard let self else { return }
                    if let url { self.finish(.success(url)) }
                    else if (error as? ASWebAuthenticationSessionError)?.code == .canceledLogin { self.finish(.failure(ZovaFailure.cancelled)) }
                    else { self.finish(.failure(ZovaFailure.unavailable)) }
                }
            }
            flow.presentationContextProvider = self
            flow.prefersEphemeralWebBrowserSession = false
            session = flow
            if !flow.start() { finish(.failure(ZovaFailure.unavailable)) }
        }
    }
    func received(_ url: URL) {
        if session != nil { finish(.success(url)) }
    }
    private func finish(_ result: Result<URL, Error>) {
        guard let callback = continuation else { return }
        let completed = session
        continuation = nil; session = nil
        completed?.cancel()
        callback.resume(with: result)
    }
}
