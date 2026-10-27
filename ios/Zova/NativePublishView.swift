import SwiftUI

struct NativePublishView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    let mode: String
    @State private var contexts: JSONValue = .null
    @State private var platforms: [String] = []
    @State private var connections: [String: Int] = [:]
    @State private var privacy = ""
    @State private var comment = false
    @State private var duet = false
    @State private var stitch = false
    @State private var aigc = false
    @State private var commercial = false
    @State private var ownBrand = false
    @State private var partnership = false
    @State private var consent = false
    @State private var date = Date().addingTimeInterval(3600)
    @State private var review: JSONValue = .null
    @State private var suggestions: JSONValue = .null
    @State private var attempted = false
    private var scheduleTimezone: String { store.draft.planned["timezone"].string.isEmpty ? store.timezone : store.draft.planned["timezone"].string }
    private var tiktok: JSONValue { contexts["tiktok"] }
    private var direct: Bool { platforms.contains("tiktok") && tiktok["posting_mode"].string != "inbox" }
    private var valid: Bool {
        !platforms.isEmpty && platforms.allSatisfy { contexts[$0]["error"].isNull && connections[$0, default: 0] > 0 } &&
        (!direct || (!privacy.isEmpty && consent && (!commercial || ownBrand || partnership) &&
        (!partnership || ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS"].contains(privacy)) &&
        (!tiktok["private_test_mode"].bool || (privacy == "SELF_ONLY" && !partnership))))
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                NativeSheetHeader(title: review.isNull ? "Review post" : mode == "schedule" ? "Confirm schedule" : "Confirm publish")
                if store.busy { ProgressView("Checking…") }
                if review.isNull {
                    settings
                    Button("Review final post") { run { try await buildReview() } }.buttonStyle(ZovaPrimary()).disabled(store.busy || !valid || attempted)
                } else {
                    NativeReviewSnapshot(snapshot: review["snapshot"])
                    Button("Edit caption / media") { review = .null; dismiss() }.buttonStyle(.bordered).disabled(store.busy || attempted)
                    Button(mode == "schedule" ? "Confirm schedule" : review["snapshot"]["targets"]["tiktok"]["requires_tiktok_completion"].bool && platforms.count == 1 ? "Send to TikTok inbox" : "Confirm publish") {
                        run { try await confirm() }
                    }.buttonStyle(ZovaPrimary()).disabled(store.busy || attempted).accessibilityIdentifier("confirm-publication")
                }
            }.padding(20)
        }.preferredColorScheme(.light).tint(ZovaDesign.purple).task { run { try await load() } }
            .onChange(of: privacy) { _, value in consent = false; if !["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS"].contains(value) { partnership = false } }
            .onChange(of: commercial) { _, value in consent = false; if !value { ownBrand = false; partnership = false } }
            .onChange(of: ownBrand) { _, _ in consent = false }.onChange(of: partnership) { _, _ in consent = false }
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
    private var settings: some View {
        VStack(alignment: .leading, spacing: 16) {
            ForEach(platforms, id: \.self) { platform in
                HStack { NativePlatformMark(platform: platform); Text(SocialPlatform(rawValue: platform)?.title ?? platform).font(.headline); Spacer() }
                if !contexts[platform]["error"].isNull {
                    Text(contexts[platform]["error"].string).font(.callout).foregroundStyle(.secondary)
                    Button("Remove from this review") { platforms.removeAll { $0 == platform } }
                } else {
                    Picker("Account", selection: Binding(get: { connections[platform, default: 0] }, set: { connections[platform] = $0; consent = false; privacy = ""; run { try await loadContexts() } })) {
                        ForEach(contexts[platform]["accounts"].array, id: \.["id"].int) { account in
                            Text(account["name"].string.isEmpty || account["name"] == account["account_id"] ? "Connected account" : account["name"].string).tag(account["id"].int)
                        }
                    }.pickerStyle(.menu).disabled(store.busy)
                }
            }
            if platforms.contains("tiktok") {
                if direct {
                    Picker("Who can see this post?", selection: $privacy) {
                        Text("Choose privacy").tag("")
                        ForEach(tiktok["privacy_options"].strings.filter { !tiktok["private_test_mode"].bool || $0 == "SELF_ONLY" }, id: \.self) { value in Text(privacyName(value)).tag(value) }
                    }.pickerStyle(.menu)
                    Toggle("Allow comments", isOn: $comment).disabled(tiktok["comment_disabled"].bool)
                    if store.draft.media.contains(where: { $0["kind"].string == "video" }) {
                        Toggle("Allow Duet", isOn: $duet).disabled(tiktok["duet_disabled"].bool)
                        Toggle("Allow Stitch", isOn: $stitch).disabled(tiktok["stitch_disabled"].bool)
                    }
                    Toggle("This media is AI-generated", isOn: $aigc)
                    Toggle("Promotes a brand, product or service", isOn: $commercial)
                    if commercial {
                        Toggle("Your brand", isOn: $ownBrand)
                        Toggle("Paid partnership", isOn: $partnership).disabled(!["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS"].contains(privacy) || tiktok["private_test_mode"].bool)
                        Text(partnership ? "TikTok labels this Paid partnership." : ownBrand ? "TikTok labels this Promotional content." : "Choose Your brand, Paid partnership, or both.").font(.caption).foregroundStyle(.secondary)
                        if !["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS"].contains(privacy) { Text("Paid partnerships require Everyone or Friends visibility.").font(.caption) }
                    }
                    if tiktok["private_test_mode"].bool { Text("TikTok testing requires Only me visibility. Paid partnerships need TikTok approval.").font(.caption) }
                    TikTokDeclaration(paid: partnership)
                    Toggle("I agree and want to post this content to TikTok", isOn: $consent)
                } else { Text("This connection sends videos to your TikTok inbox. Finish the caption, privacy and publishing in TikTok.").font(.callout) }
            }
            if mode == "schedule" {
                DatePicker("Posting time", selection: $date, in: Date()...).environment(\.timeZone, TimeZone(identifier: scheduleTimezone) ?? .current)
                Text(scheduleTimezone).font(.caption).foregroundStyle(.secondary)
                Button("Suggest starting times") { run { suggestions = try await store.request("/api/ai/schedule", method: "POST", body: .object(["platforms": .strings(platforms), "context": .string(store.draft.brief)])) } }
                if !suggestions.isNull {
                    Text(suggestions["note"].string).font(.caption)
                    Text("Suggested times in " + store.timezone).font(.caption).foregroundStyle(.secondary)
                    ForEach(suggestions["suggestions"].object.keys.sorted(), id: \.self) { platform in
                        ForEach(Array(suggestions["suggestions"][platform].array.enumerated()), id: \.offset) { _, item in
                            Button(item["label"].string + " · " + item["local_time"].string) {
                                let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd'T'HH:mm"; formatter.timeZone = TimeZone(identifier: store.timezone)
                                if let value = formatter.date(from: String(item["local_time"].string.prefix(16))) { date = value }
                            }
                        }
                    }
                }
            }
        }.disabled(store.busy)
    }
    private func privacyName(_ value: String) -> String { ["SELF_ONLY":"Only me", "PUBLIC_TO_EVERYONE":"Everyone", "MUTUAL_FOLLOW_FRIENDS":"Friends", "FOLLOWER_OF_CREATOR":"Followers"][value] ?? value }
    private func load() async throws {
        try await store.save()
        if let planned = ProductLinks.localDate(store.draft.planned["local_time"].string, timezone: scheduleTimezone), planned > Date() { date = planned }
        platforms = store.draft.selected.filter { !store.draft.variants[$0]["posts"].array.isEmpty }
        if platforms.isEmpty { throw ZovaFailure.server("Choose a platform with a caption first.") }
        try await loadContexts()
    }
    private func loadContexts() async throws {
        let reply = try await store.request("/api/publish-context", method: "POST", body: .object(["platforms": .strings(platforms), "variants": store.draft.variants, "connection_ids": .object(connections.mapValues { .integer($0) })]))
        contexts = reply["platforms"]
        for platform in platforms { connections[platform] = contexts[platform]["connection_id"].int }
        comment = false; duet = false; stitch = false; consent = false
    }
    private func buildReview() async throws {
        guard valid else { return }
        try await store.save()
        guard let id = store.draft.id else { throw ZovaFailure.invalidResponse }
        var options: JSONValue = .object([:])
        if platforms.contains("instagram") {
            options["instagram"] = .object(["format": .string(store.draft.workspace["instagram_format"].string.isEmpty ? "post" : store.draft.workspace["instagram_format"].string)])
            let audio = store.draft.workspace["instagram_audio"]
            if !audio.isNull {
                guard audio["connection_id"].int == connections["instagram"] else { throw ZovaFailure.server("Choose music for the selected Instagram account.") }
                var fields = audio.object; fields.removeValue(forKey: "connection_id"); options["instagram"]["audio"] = .object(fields)
            }
        }
        if platforms.contains("tiktok") {
            options["tiktok"] = direct ? .object(["posting_mode": .string("direct"), "privacy_level": .string(privacy), "video_duration_sec": store.draft.workspace["video_duration"].isNull ? .number(0) : store.draft.workspace["video_duration"], "allow_comment": .bool(comment), "allow_duet": .bool(duet), "allow_stitch": .bool(stitch), "commercial_content": .bool(commercial), "your_brand": .bool(ownBrand), "brand_content": .bool(partnership), "is_aigc": .bool(aigc), "consent": .bool(consent)]) : .object(["posting_mode": .string("inbox")])
        }
        var body: JSONValue = .object(["draft_id": .integer(id), "platforms": .strings(platforms), "variants": .object(store.draft.variants.object.filter { platforms.contains($0.key) }), "media_asset_ids": store.draft.mediaIDs, "link_url": .string(store.draft.workspace["link_url"].string), "publish_options": options, "connection_ids": .object(connections.mapValues { .integer($0) })])
        if mode == "schedule" { body["scheduled_local"] = .string(ISO8601DateFormatter().string(from: date)) }
        review = try await store.request("/api/publish-review", method: "POST", body: body)
    }
    private func confirm() async throws {
        guard !review.isNull, !attempted else { return }
        let snapshot = review["snapshot"]
        var body = JSONValue.object(Dictionary(uniqueKeysWithValues: ["draft_id", "platforms", "variants", "media_asset_ids", "link_url", "publish_options"].map { ($0, snapshot[$0]) }))
        body["review_token"] = review["review_token"]
        if mode == "schedule" { body["scheduled_local"] = snapshot["scheduled_utc"] }
        attempted = true
        do {
            store.results = try await store.request(mode == "schedule" ? "/api/schedule" : "/api/publish", method: "POST", body: body)
            store.draft.status = store.results["draft_status"].string
            try await store.refreshResults(); dismiss()
        } catch {
            // Once attempted, never offer an automatic resend after a lost response.
            try? await store.refreshResults(); dismiss()
            throw ZovaFailure.server("Check Publication results and the destination before retrying. Zova did not resend the request. " + error.localizedDescription)
        }
    }
}

struct TikTokDeclaration: View {
    let paid: Bool
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("By posting, you agree to TikTok’s:").font(.caption)
            if paid { Link("Branded Content Policy", destination: URL(string: "https://www.tiktok.com/legal/page/global/bc-policy/en")!) }
            Link("Music Usage Confirmation", destination: URL(string: "https://www.tiktok.com/legal/page/global/music-usage-confirmation/en")!)
        }.font(.caption)
    }
}
struct NativeReviewSnapshot: View {
    let snapshot: JSONValue
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            ForEach(snapshot["platforms"].strings, id: \.self) { platform in
                let target = snapshot["targets"][platform]
                ZovaCard {
                    HStack { NativePlatformMark(platform: platform); Text(target["display_name"].string).font(.headline) }
                    if !target["username"].string.isEmpty { Text("@" + target["username"].string).font(.caption) }
                    if target["format"].string == "story" { Text("Story: only the visual publishes for 24 hours. Caption, source link, stickers and music are not included.").font(.callout) }
                    else { ForEach(Array(target["posts"].strings.enumerated()), id: \.offset) { _, post in Text(post).textSelection(.enabled) } }
                    if !target["link"].string.isEmpty { Text("Attached link: " + target["link"].string).font(.caption) }
                    let options = snapshot["publish_options"][platform]
                    if platform == "tiktok" {
                        if target["requires_tiktok_completion"].bool { Text("Delivered to inbox only. Caption and final publication are completed in TikTok.") }
                        else {
                            Text("Visibility: " + options["privacy_level"].string.replacingOccurrences(of: "_", with: " ").capitalized).font(.callout)
                            ForEach([("Comments", "allow_comment"), ("Duet", "allow_duet"), ("Stitch", "allow_stitch"), ("Your brand", "your_brand"), ("Paid partnership", "brand_content"), ("AI-generated media", "is_aigc")], id: \.1) { label, key in Text(label + ": " + (options[key].bool ? "Yes" : "No")).font(.caption) }
                            TikTokDeclaration(paid: options["brand_content"].bool)
                            Text("TikTok may take a few minutes to process your post.").font(.caption)
                        }
                    }
                    if !options["audio"].isNull { Text("Music: " + options["audio"]["title"].string + " · " + options["audio"]["artist"].string); Text("Music \(options["audio"]["audio_volume"].int)% · Original audio \(options["audio"]["video_volume"].int)%. The combined audio cannot be previewed before publishing.").font(.caption) }
                }
            }
            ForEach(Array(snapshot["media"].array.enumerated()), id: \.offset) { index, value in
                if snapshot["media_asset_ids"].array.indices.contains(index) {
                    NativeAssetPreview(asset: .object(value.object.merging(["id": snapshot["media_asset_ids"].array[index]]) { _, new in new }))
                }
            }
            if !snapshot["link_url"].string.isEmpty { Text("Source link: " + snapshot["link_url"].string).font(.caption) }
            if let date = ProductLinks.date(snapshot["scheduled_utc"].string) {
                Text("Scheduled: " + scheduledLabel(date) + " · " + snapshot["timezone"].string).font(.headline)
            } else { Text("Publish these reviewed versions now?").font(.headline) }
        }
    }
    private func scheduledLabel(_ date: Date) -> String {
        let formatter = DateFormatter(); formatter.dateStyle = .medium; formatter.timeStyle = .short
        formatter.timeZone = TimeZone(identifier: snapshot["timezone"].string) ?? TimeZone(secondsFromGMT: 0)
        return formatter.string(from: date)
    }
}
