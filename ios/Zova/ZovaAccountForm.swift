import AuthenticationServices
import SafariServices
import SwiftUI

enum ZovaAccountScreen: Identifiable, Hashable {
    case signup, recovery, reset(String), verify(String)
    var id: Self { self }

    init?(link: URL, base: URL) {
        guard link.scheme == "https", link.host == base.host, link.port == base.port,
              link.user == nil, link.password == nil, link.query == nil,
              let fragment = link.fragment, fragment.hasPrefix("token=") else { return nil }
        let token = String(fragment.dropFirst(6))
        guard token.utf8.count == 43, token.utf8.allSatisfy({
            (65...90).contains($0) || (97...122).contains($0) || (48...57).contains($0) || $0 == 45 || $0 == 95
        }) else { return nil }
        switch link.path {
        case "/reset-password": self = .reset(token)
        case "/verify-email": self = .verify(token)
        default: return nil
        }
    }
}

struct ZovaAppleButton: View {
    @ObservedObject var session: NativeProductSession
    let acceptsTerms: Bool
    @State private var nonce: String?
    @State private var attempt = 0
    @State private var problem: String?

    var body: some View {
        VStack {
            SignInWithAppleButton(.continue) { request in
                request.requestedScopes = [.email]
                request.nonce = nonce
            } onCompletion: { result in
                guard let challenge = nonce else { return }
                nonce = nil
                Task { @MainActor in
                    session.working = true
                    defer { session.working = false; attempt += 1 }
                    do {
                        let authorization = try result.get()
                        guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                              let bytes = credential.identityToken,
                              let token = String(data: bytes, encoding: .utf8) else { throw ZovaFailure.invalidResponse }
                        try await session.api.appleLogin(token: token, nonce: challenge, acceptsTerms: acceptsTerms)
                        session.store.signedOut = false
                        try await session.store.start()
                        session.phase = .product
                    } catch let error as ASAuthorizationError where error.code == .canceled {
                        problem = nil
                    } catch { problem = error.localizedDescription }
                }
            }.frame(height: 48).disabled(nonce == nil || session.working)
            if let problem { Text(problem); Button("Retry Apple sign-in") { attempt += 1 } }
        }.task(id: attempt) {
            do { nonce = try await session.api.appleChallenge() }
            catch { problem = error.localizedDescription }
        }
    }
}

struct ZovaAccountForm: View {
    private enum Policy: String, Identifiable {
        case terms = "terms-of-service"
        case privacy = "privacy-policy"
        var id: Self { self }
    }
    @State private var policy: Policy?
    let screen: ZovaAccountScreen
    @ObservedObject var session: NativeProductSession
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var email = ""
    @State private var password = ""
    @State private var confirmation = ""
    @State private var terms = false
    @State private var working = false
    @State private var message: String?
    @State private var finished = false

    private var title: String {
        switch screen {
        case .signup: return "Create an account"
        case .verify: return "Verify email"
        default: return "Reset password"
        }
    }
    var body: some View {
        NavigationStack {
            Form {
                if !finished {
                    if screen == .signup {
                        TextField("Name", text: $name).textContentType(.name)
                        TextField("Email address", text: $email).textContentType(.emailAddress)
                            .keyboardType(.emailAddress).textInputAutocapitalization(.never).autocorrectionDisabled()
                    }
                    switch screen {
                    case .signup, .reset:
                        SecureField("New password", text: $password).textContentType(.newPassword)
                        SecureField("Confirm password", text: $confirmation).textContentType(.newPassword)
                        Text("Use 10–256 characters.")
                    default: EmptyView()
                    }
                    if screen == .signup {
                        Button("Terms of Service") { policy = .terms }
                        Button("Privacy Policy") { policy = .privacy }
                        Toggle("I accept the terms and privacy policy", isOn: $terms)
                    }
                    Button(title) { Task { await submit() } }.disabled(!ready || working)
                    if screen == .signup && terms { ZovaAppleButton(session: session, acceptsTerms: true) }
                }
                if let message { Text(message).accessibilityAddTraits(.updatesFrequently) }
            }.navigationTitle(title)
                .toolbar { Button(finished ? "Done" : "Close") { dismiss() }.disabled(working) }
        }.interactiveDismissDisabled(working)
            .sheet(item: $policy) { page in
                ZovaPolicyPage(url: session.configuration.base.appendingPathComponent(page.rawValue))
            }
    }
    private var ready: Bool {
        if case .verify = screen { return true }
        return (10...256).contains(password.count) && password == confirmation
            && (screen != .signup || (terms && !name.isEmpty && !email.isEmpty))
    }
    @MainActor private func submit() async {
        guard ready, !working else { return }
        working = true
        defer { working = false }
        do {
            switch screen {
            case .signup:
                try await session.api.accountForm(path: "/signup", fields: ["name": name, "email": email,
                    "password": password, "password_confirmation": confirmation, "accept_terms": "yes"])
                await session.login(email: email, password: password)
                message = "Account created. You can sign in with your new password."
            case let .reset(token):
                try await session.api.accountForm(path: "/reset-password", fields: ["token": token,
                    "password": password, "confirmation": confirmation])
                message = "Password updated. Sign in with your new password."
            case let .verify(token):
                try await session.api.accountForm(path: "/verify-email", fields: ["token": token])
                message = "Your email address is verified."
            case .recovery: return
            }
            finished = true
            password = ""; confirmation = ""
        } catch { message = error.localizedDescription }
    }
}

private struct ZovaPolicyPage: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> SFSafariViewController {
        SFSafariViewController(url: url)
    }
    func updateUIViewController(_ controller: SFSafariViewController, context: Context) {}
}
