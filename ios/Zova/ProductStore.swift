import SwiftUI
import AVFoundation

@MainActor
final class ProductStore: ObservableObject {
    let api: NativeAPI
    @Published var account: JSONValue = .null
    @Published var brand = 0
    @Published var draft = ProductDraft()
    @Published var drafts: [JSONValue] = []
    @Published var schedules: [JSONValue] = []
    @Published var series: [JSONValue] = []
    @Published var selectedTab = 0
    @Published var busy = false
    @Published var error: String?
    @Published var saveStatus = "Ready"
    @Published var needsConsent = false
    @Published var signedOut = false
    @Published var showReview = false
    @Published var reviewMode = "publish"
    @Published var results: JSONValue = .null
    @Published var showIntro = false
    private var autosave: Task<Void, Never>?
    private var polling: Task<Void, Never>?
    private var changeSerial = 0
    private var savedSerial = 0
    private var authority = 0
    var dirty: Bool { changeSerial != savedSerial }
    var name: String { account["profile"]["name"].string }
    var timezone: String { account["voice"]["timezone"].string.isEmpty ? "Europe/London" : account["voice"]["timezone"].string }
    init(api: NativeAPI) { self.api = api }

    func request(_ path: String, method: String = "GET", body: JSONValue? = nil) async throws -> JSONValue {
        let epoch = authority
        let result = try await api.product(path, method: method, body: body, brand: brand)
        guard epoch == authority else { throw CancellationError() }
        return result
    }
    func handle(_ error: Error) {
        if error is CancellationError { return }
        if case ZovaFailure.signInRequired = error { signedOut = true; return }
        if let issue = error as? ProductError, issue.code == "ai_permission_required" { needsConsent = true; return }
        self.error = error.localizedDescription
    }
    func perform(_ work: @escaping @MainActor () async throws -> Void) async {
        guard !busy else { return }; busy = true; error = nil
        defer { busy = false }
        do { try await work() } catch { handle(error) }
    }
    func start() async throws {
        account = try await request("/api/native/account")
        let connected = account["connections"].array.map { $0["platform"].string }
        draft.selected = SocialPlatform.allCases.map(\.rawValue).filter { connected.contains($0) }
        let intro = try await request("/api/studio/intro/claim", method: "POST", body: .object([:]))
        showIntro = intro["show"].bool
    }
    func changed() {
        changeSerial += 1; saveStatus = "Saving…"
        autosave?.cancel()
        autosave = Task { [weak self] in
            do { try await Task.sleep(for: .milliseconds(700)) } catch { return }
            guard let self, !self.busy, self.draft.editable else { return }
            await self.perform { try await self.save() }
        }
    }
    func save() async throws {
        guard draft.editable else { return }
        guard dirty || draft.id == nil else { return }
        if draft.id == nil {
            guard !draft.composer.isEmpty || !draft.brief.isEmpty || !draft.media.isEmpty || !draft.conversation.isEmpty else { return }
            let created = try await request("/api/drafts", method: "POST", body: .object([:]))
            guard created["id"].int > 0 else { throw ZovaFailure.invalidResponse }
            draft.id = created["id"].int; draft.revision = created["revision"].int
        }
        guard let id = draft.id else { return }
        let serial = changeSerial
        let reply = try await request("/api/drafts/\(id)", method: "PATCH", body: draft.payload)
        draft.revision = reply["revision"].int
        savedSerial = serial; saveStatus = dirty ? "Unsaved changes" : "Saved"
    }
    func openDraft(_ id: Int) async throws {
        try await save()
        let next = ProductDraft(try await request("/api/drafts/\(id)"))
        polling?.cancel(); results = .null
        draft = next; changeSerial = 0; savedSerial = 0; saveStatus = "Saved"; selectedTab = 0
        if !next.editable || next.status == "partial" { try await refreshResults() }
    }
    func newPost() async throws {
        try await save(); polling?.cancel(); results = .null
        let selected = draft.selected
        draft = ProductDraft(); draft.selected = selected
        changeSerial = 0; savedSerial = 0; saveStatus = "Ready"; selectedTab = 0
    }
    func switchBrand(_ id: Int) async throws {
        guard id != brand else { return }
        try await save(); authority += 1; polling?.cancel()
        brand = id; draft = ProductDraft(); results = .null
        changeSerial = 0; savedSerial = 0; drafts = []; schedules = []; series = []
        try await start(); selectedTab = 0
    }
    func reloadAccount() async throws { account = try await request("/api/native/account") }
    func loadSchedule(search: String = "") async throws {
        drafts = try await request("/api/drafts?q=" + ProductLinks.query(search)).array
        schedules = try await request("/api/schedules").array
        series = try await request("/api/series").array
    }
    func caption(_ platform: String, index: Int = 0) -> String {
        let posts = draft.variants[platform]["posts"].strings
        return posts.indices.contains(index) ? posts[index] : ""
    }
    func editCaption(_ platform: String, index: Int, text: String) {
        var posts = draft.variants[platform]["posts"].strings
        guard posts.indices.contains(index) else { return }
        posts[index] = text; draft.variants[platform]["posts"] = .strings(posts); changed()
    }
    func send(retry: Bool = false) async throws {
        guard draft.editable else { throw ZovaFailure.server("Start a new post to create another idea.") }
        let text = (retry ? draft.workspace["pending_message"].string : draft.composer).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }
        guard !draft.selected.isEmpty else { throw ZovaFailure.server("Choose a platform first.") }
        guard account["ai"]["allowed"].bool || !account["ai"]["required"].bool else { needsConsent = true; return }
        if !retry {
            draft.conversation.append(.object(["role": .string("user"), "content": .string(text), "media_asset_ids": draft.mediaIDs]))
            draft.composer = ""; draft.workspace["pending_message"] = .string(text)
            draft.workspace["pending_media_asset_ids"] = draft.mediaIDs
            draft.workspace["pending_link_url"] = draft.workspace["link_url"]
            changeSerial += 1
        }
        try await save()
        guard let id = draft.id else { throw ZovaFailure.invalidResponse }
        let plan = try await request("/api/conversation/plan", method: "POST", body: .object([
            "draft_id": .integer(id), "message": .string(text), "selected_platforms": .strings(draft.selected),
            "active_platform": .string(draft.active), "media_asset_ids": draft.mediaIDs,
            "recent_messages": .array(draft.conversation.suffix(12).map { .object(["role": $0["role"], "content": $0["content"]]) })]))
        let action = plan["action"].string
        let platforms = plan["platforms"].strings
        if action == "create" || action == "add_platforms" {
            let brief = plan["brief"].string.isEmpty ? text : plan["brief"].string
            let fresh = action == "create" && !draft.variants.object.isEmpty
            var body: JSONValue = .object(["brief": .string(action == "add_platforms" ? draft.brief : brief),
                "instruction": .string(action == "add_platforms" ? text : draft.instruction), "platforms": .strings(platforms),
                "media_asset_ids": draft.mediaIDs, "link_url": draft.workspace["link_url"], "thread_length": .integer(draft.threadLength)])
            if body["link_url"].isNull { body["link_url"] = .string("") }
            if fresh { body["source_draft_id"] = .integer(id); body["source_revision"] = .integer(draft.revision) }
            else { body["draft_id"] = .integer(id) }
            let generated = try await request("/api/ai/generate", method: "POST", body: body)
            let generatedID = generated["draft_id"].int
            guard generatedID > 0 else { throw ZovaFailure.invalidResponse }
            draft = ProductDraft(try await request("/api/drafts/\(generatedID)"))
            draft.active = platforms.first ?? draft.active
            if fresh { draft.selected = platforms }
        } else if action == "rewrite" {
            var updated = draft.variants
            for platform in platforms {
                let reply = try await request("/api/ai/rewrite", method: "POST", body: .object([
                    "platform": .string(platform), "posts": draft.variants[platform]["posts"], "instruction": .string(String((plan["brief"].string.isEmpty ? text : plan["brief"].string).prefix(1000))), "media_asset_ids": draft.mediaIDs]))
                updated[platform]["posts"] = reply["posts"]
            }
            draft.addHistory(); draft.variants = updated
        } else if action == "insight" {
            let reply = try await request("/api/insights", method: "POST", body: .object(["question": .string(String(text.prefix(2000))), "days": .integer(7)]))
            draft.conversation.append(.object(["role": .string("assistant"), "content": reply["answer"]]))
        } else if action == "publish" || action == "schedule" {
            reviewMode = action; showReview = true
        } else if !plan["reply"].string.isEmpty {
            draft.conversation.append(.object(["role": .string("assistant"), "content": plan["reply"]]))
        }
        draft.workspace["pending_message"] = .string("")
        draft.workspace["pending_media_asset_ids"] = .array([])
        changeSerial += 1; try await save()
    }
    func upload(_ url: URL, name: String, mime: String) async throws {
        guard draft.editable else { throw ZovaFailure.server("Start a new post to attach media.") }
        let video = mime.hasPrefix("video/")
        guard draft.media.count < 10, !(video && !draft.media.isEmpty), !draft.media.contains(where: { $0["kind"].string == "video" }) else {
            throw ZovaFailure.server("Use one video or up to ten images per post.")
        }
        let epoch = authority
        let response = try await api.upload(file: url, name: name, mime: mime, brand: brand)
        guard epoch == authority else { throw CancellationError() }
        let media = draft.media + response["assets"].array
        draft.workspace["media"] = .array(media); draft.workspace["media_asset_ids"] = .array(media.map { $0["id"] })
        if video {
            let asset = AVURLAsset(url: url)
            if let duration = try? await asset.load(.duration), duration.seconds.isFinite {
                draft.workspace["video_duration"] = .number(duration.seconds)
            }
        }
        changeSerial += 1; try await save()
    }
    func removeMedia(_ id: Int) {
        let media = draft.media.filter { $0["id"].int != id }
        draft.workspace["media"] = .array(media); draft.workspace["media_asset_ids"] = .array(media.map { $0["id"] })
        draft.workspace["instagram_audio"] = .null; changed()
    }
    func refreshResults() async throws {
        guard let id = draft.id else { return }
        let reply = try await request("/api/publications/\(id)")
        guard draft.id == id else { return }
        results = reply
        if !reply["draft_status"].string.isEmpty { draft.status = reply["draft_status"].string }
        polling?.cancel()
        let pending = reply["results"].object.values.contains { value in
            (["pending", "publishing", "queued"].contains(value["status"].string) && !value["delivered_to_inbox"].bool) ||
            (value["status"].string == "published" && value["privacy_level"].string == "PUBLIC_TO_EVERYONE" && value["url"].string.isEmpty)
        }
        if pending {
            polling = Task { [weak self] in
                do { try await Task.sleep(for: .seconds(15)); guard let self, self.draft.id == id else { return }; try await self.refreshResults() }
                catch { if !(error is CancellationError) { self?.handle(error) } }
            }
        }
    }
    func clear() {
        authority += 1; autosave?.cancel(); polling?.cancel()
        draft = ProductDraft(); drafts = []; schedules = []; series = []; account = .null; results = .null
    }
}
