import SwiftUI

struct NativeAccountView: View {
    @EnvironmentObject var store: ProductStore
    @ObservedObject var session: NativeProductSession
    @Binding var strategy: Bool
    @State private var name = ""
    @State private var voice: [String: String] = [:]
    @State private var preferredLength = 220
    @State private var currentPassword = ""
    @State private var newPassword = ""
    @State private var confirmation = ""
    @State private var brandName = ""
    @State private var deleteSheet = false
    @State private var guide = false
    @State private var saved = ""
    @State private var unlinkID: Int?
    @State private var devices: JSONValue = .null
    @State private var timezonePicker = false
    private let voiceFields = [("Writing tone", "writing_tone"), ("Audience", "audience"), ("Topics", "topics"), ("Things to avoid", "things_to_avoid"), ("Writing examples", "example_posts"), ("Account timezone", "timezone")]
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                Text("Account").font(.title2.bold())
                NativeAdaptiveRow { VStack(alignment: .leading, spacing: 5) { Text(store.name).font(.headline); Text(store.account["profile"]["email"].string).font(.caption).foregroundStyle(.secondary) }; Button("Sign out") { run { try await store.save(); await session.logout() } }.font(.caption).frame(minWidth: 44, minHeight: 44).disabled(store.busy) }
                if store.busy { ProgressView(session.connectingPlatform.map { "Connecting to " + $0 + "…" } ?? "Updating…") }
                if !saved.isEmpty { Text(saved).font(.callout).foregroundStyle(ZovaDesign.violet).frame(maxWidth: .infinity).multilineTextAlignment(.center).accessibilityAddTraits(.updatesFrequently) }
                group("Your details", icon: "person") {
                    NativeField(title: "Name", text: $name, lines: 1)
                    Button("Save details") { run { _ = try await store.api.form("/account/profile", fields: ["display_name": name], brand: store.brand); try await store.reloadAccount(); saved = "Details saved." } }.buttonStyle(ZovaPrimary())
                    if !store.account["profile"]["email_verified"].bool {
                        Text("Email not verified").font(.caption).foregroundStyle(.secondary)
                        Button("Send verification email") { run { _ = try await store.api.form("/account/verify-email", fields: [:], brand: store.brand); saved = "Check your inbox for the verification email." } }.buttonStyle(ZovaPrimary())
                    }
                }
                Button { strategy = true } label: { row("Your strategy", icon: "sparkles", arrow: "arrow.up.right") }
                group("Your voice", icon: "waveform") {
                    Text("Your edits take priority. With AI sharing on, approved captions shape your next draft.").font(.callout).foregroundStyle(.secondary)
                    ForEach(voiceFields.filter { $0.1 != "timezone" }, id: \.1) { title, key in NativeField(title: title, text: Binding(get: { voice[key] ?? "" }, set: { voice[key] = $0 }), lines: 2) }
                    Button { timezonePicker = true } label: { HStack { Text("Timezone"); Spacer(); Text((voice["timezone"] ?? store.timezone).replacingOccurrences(of: "_", with: " ")); Image(systemName: "chevron.right") }.font(.callout).frame(minHeight: 44) }
                    Stepper("Typical caption · \(preferredLength) characters", value: $preferredLength, in: 30...4000, step: 10)
                    Button("Save voice") { run { var fields = voice; fields["preferred_post_length"] = String(preferredLength); _ = try await store.api.form("/account/preferences", fields: fields, brand: store.brand); try await store.reloadAccount(); fillVoice(); saved = "Voice saved." } }.buttonStyle(ZovaPrimary())
                    Button("Scan recent posts") { run { let reply = try await store.request("/api/voice/scan-socials", method: "POST", body: .object([:])); try await store.reloadAccount(); fillVoice(); saved = reply["message"].string.isEmpty ? "Voice refreshed." : reply["message"].string } }.frame(minHeight: 44)
                    Button("Learn from my writing examples") { run { _ = try await store.request("/api/voice/learn", method: "POST", body: .object(["content": .string(voice["example_posts"] ?? "")])); try await store.reloadAccount(); fillVoice(); saved = "Voice refreshed from your examples." } }.disabled((voice["example_posts"] ?? "").count < 80)
                    if !(voice["example_posts"] ?? "").isEmpty && (voice["example_posts"] ?? "").count < 80 { Text("Add at least 80 characters of examples to learn your voice.").font(.caption) }
                    if !store.account["voice"]["approved_examples"].array.isEmpty {
                        DisclosureGroup("Recent approved captions") {
                            ForEach(Array(store.account["voice"]["approved_examples"].strings.enumerated()), id: \.offset) { _, text in Text(text).font(.callout).padding(.vertical, 8) }
                            Button("Clear remembered captions") { run { _ = try await store.api.form("/account/voice/clear-examples", fields: [:], brand: store.brand); try await store.reloadAccount(); saved = "Remembered captions cleared." } }
                        }
                    }
                }
                group("Social accounts", icon: "link") {
                    ForEach(SocialPlatform.allCases) { platform in
                        VStack(alignment: .leading, spacing: 12) {
                            HStack { NativePlatformMark(platform: platform.rawValue, light: true); Text(platform.title).font(.headline) }
                            let connections = store.account["connections"].array.filter { $0["platform"].string == platform.rawValue }
                            if connections.isEmpty { Text("Not connected").font(.callout).foregroundStyle(.secondary) }
                            ForEach(connections, id: \.["id"].int) { connection in
                                NativeAdaptiveRow { Text(connection["name"].string + (connection["status"].string == "reconnect" ? " · Reconnect needed" : connection["status"].string == "unavailable" ? " · Check unavailable" : " · Connected")).font(.callout); Button("Unlink", role: .destructive) { unlinkID = connection["id"].int }.font(.caption).frame(minWidth: 44, minHeight: 44) }
                            }
                            Button(connections.isEmpty ? "Connect " + platform.title : "Connection options") { Task { await session.connect(platform.rawValue) } }.buttonStyle(ZovaPrimary())
                            if platform == .instagram { Text("Creator or Business account required. You can also connect through Facebook if linked to a Page.").font(.caption).foregroundStyle(.secondary) }
                        }.padding(.vertical, 10)
                        Divider()
                    }
                }
                group("Brands", icon: "square.stack") {
                    ForEach(store.account["brand"]["choices"].array, id: \.["id"].int) { item in
                        Button { run { try await store.switchBrand(item["id"].int) } } label: { HStack { Text(item["name"].string); Spacer(); if item["id"].int == store.brand { Image(systemName: "checkmark") } } }.frame(minHeight: 44)
                    }
                    NativeField(title: "Brand name", text: $brandName, lines: 1)
                    HStack {
                        Button("Add brand") { run { _ = try await store.api.form("/brands", fields: ["name": brandName], brand: store.brand); try await store.reloadAccount(); brandName = store.account["brand"]["name"].string; saved = "Brand added." } }.buttonStyle(ZovaPrimary())
                        Button("Rename current") { run { _ = try await store.api.form("/brands/\(store.brand)/name", fields: ["name": brandName], brand: store.brand); try await store.reloadAccount(); saved = "Brand renamed." } }.buttonStyle(ZovaPrimary())
                    }.disabled(brandName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                group("Security & privacy", icon: "checkmark.shield") {
                    NativePasswordField(title: "Current password", text: $currentPassword)
                    NativePasswordField(title: "New password", text: $newPassword, newPassword: true)
                    NativePasswordField(title: "Confirm new password", text: $confirmation, newPassword: true)
                    Label("10–256 characters", systemImage: (10...256).contains(newPassword.count) ? "checkmark.circle.fill" : "circle").font(.caption)
                    Label("Passwords match", systemImage: !confirmation.isEmpty && newPassword == confirmation ? "checkmark.circle.fill" : "circle").font(.caption)
                    Button("Update password") { run {
                        _ = try await store.api.form("/account/password", fields: ["current_password": currentPassword, "new_password": newPassword, "new_password_confirmation": confirmation], brand: store.brand)
                        currentPassword = ""; newPassword = ""; confirmation = ""; await session.logout()
                    } }.buttonStyle(ZovaPrimary()).disabled(currentPassword.isEmpty || !(10...256).contains(newPassword.count) || newPassword != confirmation)
                    Text("Changing your password signs out existing sessions.").font(.caption).foregroundStyle(.secondary)
                    Button("Review AI sharing") { store.needsConsent = true }
                    Text(store.account["ai"]["allowed"].bool ? "AI sharing is on." : "AI sharing is off.").font(.caption)
                    Button("iPhone sessions") { run { devices = try await store.api.deviceSessions() } }
                    ForEach(devices["sessions"].array, id: \.["id"].string) { device in
                        HStack { Text(device["current"].bool ? "This iPhone" : "iPhone session"); Spacer(); Button("Revoke") { run { try await store.api.revokeDevice(device["id"].string); if device["current"].bool { await session.logout() } else { devices = try await store.api.deviceSessions() } } } }.font(.callout)
                    }
                    legal("Security information", "/security"); legal("Privacy", "/privacy-policy"); legal("Terms", "/terms-of-service")
                }
                group("Plan & help", icon: "questionmark.circle") {
                    Text("Testing access").font(.headline)
                    Text("Customer charges are disabled. No payment card is needed for this beta.").font(.callout).foregroundStyle(.secondary)
                    Button("Guide") { guide = true }
                    Link("Contact support", destination: URL(string: "mailto:support@zova-social.com")!)
                }
                Button(role: .destructive) { deleteSheet = true } label: { row("Delete account", icon: "trash", arrow: "chevron.right") }
            }.padding(22).disabled(store.busy)
        }.background(ZovaDesign.dark).foregroundStyle(.white).tint(ZovaDesign.violet)
            .task { name = store.name; brandName = store.account["brand"]["name"].string; fillVoice() }
            .onChange(of: store.account["brand"]["id"].int) { _, _ in brandName = store.account["brand"]["name"].string; fillVoice(); saved = "" }
            .scrollDismissesKeyboard(.interactively)
            .sheet(isPresented: $timezonePicker) { NativeTimezonePicker(selection: Binding(get: { voice["timezone"] ?? store.timezone }, set: { voice["timezone"] = $0 })) }
            .sheet(isPresented: $guide) { NativeGuideView().environmentObject(store) }
            .sheet(isPresented: $deleteSheet) { NativeDeletionView(session: session).environmentObject(store) }
            .confirmationDialog("Unlink this account? Unsent posts using this connection will be cancelled.", isPresented: Binding(get: { unlinkID != nil }, set: { if !$0 { unlinkID = nil } })) {
                Button("Unlink", role: .destructive) { guard let id = unlinkID else { return }; unlinkID = nil; run { _ = try await store.api.form("/account/connections/\(id)/unlink", fields: [:], brand: store.brand); try await store.reloadAccount() } }
            }
            .onDisappear { currentPassword = ""; newPassword = ""; confirmation = "" }
            .onChange(of: store.selectedTab) { _, index in if index != 3 { currentPassword = ""; newPassword = ""; confirmation = "" } }
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform { saved = ""; try await work() } } }
    private func fillVoice() { for (_, key) in voiceFields { voice[key] = store.account["voice"][key].string }; preferredLength = max(30, min(4000, store.account["voice"]["preferred_post_length"].int)) }
    private func row(_ title: String, icon: String, arrow: String) -> some View { HStack(spacing: 14) { Image(systemName: icon).frame(width: 24); Text(title).font(.headline); Spacer(); Image(systemName: arrow).font(.caption) }.frame(minHeight: 44) }
    private func group<Content: View>(_ title: String, icon: String, @ViewBuilder content: @escaping () -> Content) -> some View {
        VStack(spacing: 14) { DisclosureGroup(isExpanded: Binding(get: { store.accountSection == title }, set: { store.accountSection = $0 ? title : "" })) { VStack(alignment: .leading, spacing: 16, content: content).padding(.vertical, 16) } label: { HStack(spacing: 14) { Image(systemName: icon).frame(width: 24); Text(title).font(.headline) }.frame(minHeight: 44) }; Divider().overlay(.white.opacity(0.15)) }
    }
    private func legal(_ title: String, _ path: String) -> some View { Link(title, destination: try! session.configuration.endpoint(path)) }
}

struct NativeAIConsentView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            NativeSheetHeader(title: "AI sharing")
            Image(systemName: "sparkles").font(.largeTitle).foregroundStyle(ZovaDesign.purple)
            Text("Let Zova help shape your ideas").font(.title2.bold())
            Text("When you request AI help, Zova sends relevant ideas, captions, strategy, voice and available performance to OpenAI. Attachments can include resized images or sampled video frames. Audio isn’t analysed.")
            Text("You can change this in Account. Your social passwords and access tokens are not sent to AI.").font(.callout).foregroundStyle(.secondary)
            Button("Allow AI sharing") { choose(true) }.buttonStyle(ZovaPrimary())
            Button(store.account["ai"]["allowed"].bool ? "Turn off AI sharing" : "Not now") { if store.account["ai"]["allowed"].bool { choose(false) } else { dismiss() } }.frame(minHeight: 44)
            Spacer()
        }.padding(22).preferredColorScheme(.light).disabled(store.busy)
    }
    private func choose(_ allowed: Bool) { Task { await store.perform { _ = try await store.request("/api/privacy/ai", method: "POST", body: .object(["allowed": .bool(allowed), "version": store.account["ai"]["version"]])); try await store.reloadAccount(); dismiss() } } }
}

struct NativeDeletionView: View {
    @ObservedObject var session: NativeProductSession
    @EnvironmentObject var store: ProductStore
    @State private var password = ""
    @State private var confirmation = ""
    @State private var proof = ""
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            NativeSheetHeader(title: "Delete account")
            Text("This closes your account, revokes access and cancels unsent posts. Your deletion request is then handled under Zova’s deletion policy.")
            Text("Deletion is irreversible. Save any work you need before continuing.").font(.headline)
            SecureField("Current password", text: $password).textContentType(.password).textFieldStyle(.roundedBorder)
            NativeField(title: "Type DELETE to confirm", text: $confirmation, lines: 1)
            Button("Delete my account", role: .destructive) {
                Task { await store.perform {
                    let reply = try await store.api.form("/account/deletion", fields: ["confirmation": confirmation, "current_password": password, "proof": proof], brand: store.brand)
                    let receipt = ProductLinks.deletionReceipt(reply["destination"].string, configuration: session.configuration)
                    password = ""; await session.logout(); session.deletionReceipt = receipt
                    session.message = "Your deletion request was received. Account access is closed; data erasure is still pending."
                } }
            }.buttonStyle(.borderedProminent).tint(.red).disabled(store.busy || confirmation != "DELETE" || password.isEmpty || proof.isEmpty)
            Link("Deletion policy", destination: try! session.configuration.endpoint("/data-deletion"))
        }.padding(22) }.preferredColorScheme(.light).task { await store.perform { proof = try await store.request("/api/native/deletion-confirmation")["proof"].string } }.onDisappear { password = "" }
    }
}

struct NativeGuideView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    var introduction = false
    @State private var page = 0
    private let steps = [("square.and.pencil", "Start with an idea", "Choose your platforms, add photos or video, and tell Zova what you want to post."), ("sparkles", "Make it yours", "Edit the proposed caption directly. Next move offers ideas shaped by your strategy, voice and available results."), ("calendar", "You choose what goes live", "Review the account, content and settings. Publish now or pick a time. Saved work lives in Schedule.")]
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 24) {
            NativeSheetHeader(title: introduction ? "Welcome to Studio" : "Guide")
            ForEach(introduction ? [page] : Array(steps.indices), id: \.self) { index in
                ZovaCard { Image(systemName: steps[index].0).font(.largeTitle).foregroundStyle(ZovaDesign.purple); Text(steps[index].1).font(.title2.bold()); Text(steps[index].2) }
            }
            if introduction {
                Button(page == 2 ? "Start creating" : "Next") { if page < 2 { page += 1; NativeResumeState.saveIntro(page, user: store.account["profile"]["id"].int) } else { finish() } }.buttonStyle(ZovaPrimary())
                Button("Skip intro") { finish() }.frame(minHeight: 44)
            } else {
                Text("Your work and accounts").font(.headline)
                Text("One post is a single update. An X thread is a series of connected posts, read in order.")
                Text("Drafts save to your brand. Use Your posts to reopen a conversation. Schedule includes drafts, upcoming posts, a calendar and recurring series. Changing a scheduled caption first stops its unsent deliveries; review it again before scheduling.")
                Text("Connections and media").font(.headline)
                Text("Connect each social account separately in Account. Instagram requires a Creator or Business account. Supported video destinations are Instagram and TikTok. Instagram photos and Stories finish music selection in Instagram; eligible Reels can choose music before review.")
                Text("Publication results").font(.headline)
                Text("Processing means the platform has not finished. Outcome unconfirmed means check the destination before retrying. TikTok inbox delivery still needs completion in TikTok. Public links appear when a provider supplies one.")
                Text("Privacy and recovery").font(.headline)
                Text("AI sharing is optional and can be changed in Account. Your password, voice, social connections and deletion options are also there. If a save fails, retain the screen and retry; conflicting edits must be resolved before continuing.")
                Link("Full web Guide ↗", destination: URL(string: "https://zova-social.com/guide")!)
                Link("Contact support", destination: URL(string: "mailto:support@zova-social.com")!)
            }
        }.padding(22) }.preferredColorScheme(.light)
            .onAppear { if introduction { page = max(0, min(2, NativeResumeState.intro(user: store.account["profile"]["id"].int) ?? 0)) } }
            .onDisappear { if introduction { NativeResumeState.saveIntro(-1, user: store.account["profile"]["id"].int) } }
    }
    private func finish() { NativeResumeState.saveIntro(-1, user: store.account["profile"]["id"].int); dismiss() }
}
