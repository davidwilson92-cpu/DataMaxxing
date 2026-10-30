import SwiftUI
import AVFoundation

@MainActor
final class ProductStore: ObservableObject {
    let api: NativeAPI
    @Published var account: JSONValue = .null
    @Published var brand = 0
    @Published var draft = ProductDraft()
    @Published var drafts: [JSONValue] = []
    @Published var moreDrafts = false
    @Published var schedules: [JSONValue] = []
    @Published var series: [JSONValue] = []
    @Published var selectedTab = 0
    @Published var accountSection = ""
    @Published var busy = false
    @Published var backgroundSaving = false
    @Published var error: String?
    @Published var saveStatus = "Ready"
    @Published var needsConsent = false
    @Published var signedOut = false
    @Published var showReview = false
    @Published var reviewMode = "publish"
    @Published var results: JSONValue = .null
    @Published var showIntro = false
    @Published var mediaNotice = ""
    private var autosave: Task<Void, Never>?
    private var polling: Task<Void, Never>?
    private var changeSerial = 0
    private var savedSerial = 0
    private var authority = 0
    private var pendingReview = false
    private var draftOffset = 0
    private var saveWaiters: [CheckedContinuation<Void, Never>] = []
    @Published var recovery: JSONValue = .null
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
        if error is CancellationError || (error as? URLError)?.code == .cancelled || Task.isCancelled { return }
        if case ZovaFailure.signInRequired = error { signedOut = true; return }
        if let issue = error as? ProductError, issue.code == "ai_permission_required" { needsConsent = true; return }
        if let issue = error as? ProductError, issue.status == 409, dirty { recovery = NativeDraftRecovery.load(owner: recoveryOwner) }
        self.error = error.localizedDescription
    }
    func perform(_ work: @escaping @MainActor () async throws -> Void) async {
        let epoch = authority
        // A tap can arrive in the same frame as autosave starts. Finish that
        // PATCH before using its revision; never silently discard the tap.
        if busy && backgroundSaving {
            await withCheckedContinuation { saveWaiters.append($0) }
        }
        guard epoch == authority, !Task.isCancelled, !busy else { return }; busy = true; error = nil
        var succeeded = false
        defer {
            busy = false
            let waiting = saveWaiters; saveWaiters.removeAll()
            waiting.forEach { $0.resume() }
            if succeeded, pendingReview { pendingReview = false; showReview = true }
            if succeeded, dirty { queueAutosave() }
        }
        do { try await work(); succeeded = true } catch { saveStatus = dirty ? "Not saved — try again" : saveStatus; handle(error) }
    }
    func start(restoreBrand: Bool = true) async throws {
        account = try await request("/api/native/account")
        let user = account["profile"]["id"].int
        let lastBrand = NativeResumeState.brand(user: user)
        if restoreBrand, lastBrand != brand, account["brand"]["choices"].array.contains(where: { $0["id"].int == lastBrand }) {
            brand = lastBrand; account = try await request("/api/native/account")
        }
        let connected = account["connections"].array.filter { $0["status"].string != "reconnect" }.map { $0["platform"].string }
        draft.selected = SocialPlatform.allCases.map(\.rawValue).filter { connected.contains($0) }
        recovery = NativeDraftRecovery.load(owner: recoveryOwner)
        let lastDraft = NativeResumeState.draft(user: user, brand: brand)
        if recovery.isNull, lastDraft > 0 {
            do { try await openDraft(lastDraft) }
            catch let error as ProductError where error.status == 404 { NativeResumeState.saveDraft(nil, user: user, brand: brand) }
        }
        do {
            let intro = try await request("/api/studio/intro/claim", method: "POST", body: .object([:]))
            if intro["show"].bool { NativeResumeState.saveIntro(0, user: user) }
            showIntro = intro["show"].bool || (NativeResumeState.intro(user: user).map { $0 >= 0 } ?? false)
        } catch ZovaFailure.signInRequired { throw ZovaFailure.signInRequired }
        catch is CancellationError { throw CancellationError() }
        catch { showIntro = false } // Optional guidance must not block a valid account.
    }
    func changed() {
        changeSerial += 1; saveStatus = "Saving…"
        persistRecovery()
        queueAutosave()
    }
    private func queueAutosave() {
        autosave?.cancel()
        autosave = Task { [weak self] in
            do { try await Task.sleep(for: .milliseconds(700)) } catch { return }
            guard let self, !self.busy, self.draft.editable else { return }
            // Cancel only the debounce timer. Cancelling an in-flight PATCH
            // leaves an ambiguous server revision when the user keeps typing.
            self.autosave = nil
            self.backgroundSaving = true
            defer { self.backgroundSaving = false }
            await self.perform { try await self.save() }
        }
    }
    func save() async throws {
        guard draft.editable else { return }
        guard dirty || draft.id == nil else { return }
        persistRecovery()
        if draft.id == nil {
            guard !draft.composer.isEmpty || !draft.brief.isEmpty || !draft.media.isEmpty || !draft.conversation.isEmpty else {
                savedSerial = changeSerial; saveStatus = "Ready"; NativeDraftRecovery.remove(owner: recoveryOwner); return
            }
            let created = try await request("/api/drafts", method: "POST", body: .object([:]))
            guard created["id"].int > 0 else { throw ZovaFailure.invalidResponse }
            draft.id = created["id"].int; draft.revision = created["revision"].int
        }
        guard let id = draft.id else { return }
        let serial = changeSerial
        let reply = try await request("/api/drafts/\(id)", method: "PATCH", body: draft.payload)
        draft.revision = reply["revision"].int
        savedSerial = serial; saveStatus = dirty ? "Unsaved changes" : "Saved"
        NativeResumeState.saveDraft(id, user: account["profile"]["id"].int, brand: brand)
        if dirty { persistRecovery() } else { NativeDraftRecovery.remove(owner: recoveryOwner) }
    }
    func openDraft(_ id: Int) async throws {
        try await save()
        let next = ProductDraft(try await request("/api/drafts/\(id)"))
        polling?.cancel(); results = .null
        draft = next; changeSerial = 0; savedSerial = 0; saveStatus = "Saved"; selectedTab = 0
        NativeResumeState.saveDraft(id, user: account["profile"]["id"].int, brand: brand)
        mediaNotice = ""
        if !next.editable || next.status == "partial" { try await refreshResults() }
    }
    func newPost() async throws {
        try await save(); polling?.cancel(); results = .null
        let selected = draft.selected
        draft = ProductDraft(); draft.selected = selected; mediaNotice = ""
        NativeResumeState.saveDraft(nil, user: account["profile"]["id"].int, brand: brand)
        changeSerial = 0; savedSerial = 0; saveStatus = "Ready"; selectedTab = 0
    }
    func switchBrand(_ id: Int) async throws {
        guard id != brand else { return }
        try await save(); authority += 1; polling?.cancel()
        brand = id; draft = ProductDraft(); results = .null; mediaNotice = ""
        changeSerial = 0; savedSerial = 0; drafts = []; schedules = []; series = []
        NativeResumeState.saveBrand(id, user: account["profile"]["id"].int)
        try await start(restoreBrand: false); selectedTab = 0
    }
    func reloadAccount() async throws { account = try await request("/api/native/account") }
    func refreshConnections() async {
        guard !busy, !account["connections"].array.isEmpty else { return }
        do { _ = try await request("/api/connections/check", method: "POST", body: .object([:])); try await reloadAccount() }
        catch ZovaFailure.signInRequired { signedOut = true }
        catch { } // Offline checks retain the previous status; never claim a revocation.
    }
    func loadSchedule(search: String = "") async throws {
        try await loadDrafts(search: search)
        schedules = try await request("/api/schedules").array
        series = try await request("/api/series").array
    }
    func loadDrafts(search: String = "", more: Bool = false, status: String = "all") async throws {
        let offset = more ? draftOffset : 0
        let rows = try await request("/api/drafts?q=" + ProductLinks.query(search) + "&offset=\(offset)&status=" + ProductLinks.query(status)).array
        if !more { drafts = [] }
        let existing = Set(drafts.map { $0["id"].int })
        drafts += rows.filter { !existing.contains($0["id"].int) }
        draftOffset = offset + rows.count; moreDrafts = rows.count == 100
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
        if retry && (draft.workspace["pending_media_asset_ids"] != draft.mediaIDs || draft.workspace["pending_link_url"].string != draft.workspace["link_url"].string) {
            throw ZovaFailure.server("Your attachment or source link changed. Send a new message to use the current selection.")
        }
        guard account["ai"]["allowed"].bool || !account["ai"]["required"].bool else { needsConsent = true; return }
        if !retry {
            let sentMedia = draft.unsentMedia
            draft.conversation.append(.object(["role": .string("user"), "content": .string(text), "media_asset_ids": .array(sentMedia.map { $0["id"] }), "media": .array(sentMedia)]))
            draft.composer = ""; draft.workspace["pending_message"] = .string(text)
            draft.workspace["pending_media_asset_ids"] = draft.mediaIDs
            draft.workspace["pending_link_url"] = draft.workspace["link_url"]
            changeSerial += 1; persistRecovery()
        }
        try await save()
        guard let id = draft.id else { throw ZovaFailure.invalidResponse }
        let plan = try await request("/api/conversation/plan", method: "POST", body: .object([
            "draft_id": .integer(id), "message": .string(text), "selected_platforms": .strings(draft.selected),
            "platform_selection_explicit": .bool(draft.workspace["platform_selection_explicit"].bool),
            "active_platform": .string(draft.active), "media_asset_ids": draft.mediaIDs,
            "recent_messages": .array(draft.conversation.suffix(12).map { .object(["role": $0["role"], "content": $0["content"]]) })]))
        var action = plan["action"].string
        mediaNotice = plan["media_inspection"].array.contains(where: { $0["status"].string != "inspected" }) ? "Some media could not be inspected. Check the caption against your upload." : ""
        var platforms = plan["platforms"].strings.isEmpty ? draft.selected : plan["platforms"].strings
        if ["publish", "schedule"].contains(action) && !draft.variants.object.values.contains(where: { $0["posts"].strings.contains(where: { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }) }) { action = "create"; platforms = draft.selected }
        if action == "create" || action == "add_platforms" {
            let previousSelection = draft.selected
            if action == "add_platforms" { platforms = platforms.filter { draft.variants[$0].isNull } }
            guard !platforms.isEmpty else { throw ZovaFailure.server("Those versions already exist. Tell Zova what to change in them.") }
            let brief = plan["brief"].string.isEmpty ? text : plan["brief"].string
            let fresh = action == "create" && !draft.variants.object.isEmpty
            var body: JSONValue = .object(["brief": .string(action == "add_platforms" ? draft.brief : brief),
                "instruction": .string(writingInstruction(action == "add_platforms" ? text : draft.instruction, instagram: platforms.contains("instagram"))), "platforms": .strings(platforms),
                "media_asset_ids": draft.mediaIDs, "link_url": draft.workspace["link_url"], "thread_length": .integer(draft.threadLength)])
            if body["link_url"].isNull { body["link_url"] = .string("") }
            if fresh { body["source_draft_id"] = .integer(id); body["source_revision"] = .integer(draft.revision) }
            else { body["draft_id"] = .integer(id) }
            let generated = try await request("/api/ai/generate", method: "POST", body: body)
            let generatedID = generated["draft_id"].int
            guard generatedID > 0 else { throw ZovaFailure.invalidResponse }
            draft = ProductDraft(try await request("/api/drafts/\(generatedID)"))
            draft.active = platforms.first ?? draft.active
            draft.selected = action == "add_platforms" ? SocialPlatform.allCases.map(\.rawValue).filter { (previousSelection + platforms).contains($0) } : platforms
        } else if action == "rewrite" {
            var updated = draft.variants
            for platform in platforms {
                guard !draft.variants[platform]["posts"].array.isEmpty else { throw ZovaFailure.server("Add a \(SocialPlatform(rawValue: platform)?.title ?? platform) version first.") }
                let reply = try await request("/api/ai/rewrite", method: "POST", body: .object([
                    "platform": .string(platform), "posts": draft.variants[platform]["posts"], "instruction": .string(writingInstruction(String((plan["brief"].string.isEmpty ? text : plan["brief"].string).prefix(700)), instagram: platform == "instagram")), "media_asset_ids": draft.mediaIDs]))
                updated[platform]["posts"] = reply["posts"]
            }
            draft.addHistory(); draft.variants = updated
        } else if action == "insight" {
            let reply = try await request("/api/insights", method: "POST", body: .object(["question": .string(String(text.prefix(2000))), "days": .integer(7)]))
            draft.conversation.append(.object(["role": .string("assistant"), "content": reply["answer"]]))
            draft.workspace["conversation_kind"] = .string("insight")
        } else if action == "publish" || action == "schedule" {
            reviewMode = action
        } else if !plan["reply"].string.isEmpty {
            draft.conversation.append(.object(["role": .string("assistant"), "content": plan["reply"]]))
        }
        draft.workspace["pending_message"] = .string("")
        draft.workspace["pending_media_asset_ids"] = .array([])
        changeSerial += 1; try await save()
        if action == "publish" || action == "schedule" { pendingReview = true }
    }
    private func writingInstruction(_ value: String, instagram: Bool) -> String {
        guard instagram && draft.workspace["instagram_format"].string == "story" else { return value }
        return String(value.prefix(4400)) + "\nFor Instagram only: write concise Story planning copy for one visual, not a feed caption or hashtags. Text is a separate planning note; do not claim it is added to the uploaded visual."
    }
    func validateAttachments(_ mimes: [String]) throws {
        let count = draft.media.count + mimes.count
        let video = mimes.contains(where: { $0.hasPrefix("video/") }) || draft.media.contains(where: { $0["kind"].string == "video" })
        guard count <= 10, !video || count == 1 else { throw ZovaFailure.server("Use one video or up to ten images per post.") }
    }
    func upload(_ url: URL, name: String, mime: String) async throws {
        guard draft.editable else { throw ZovaFailure.server("Start a new post to attach media.") }
        let video = mime.hasPrefix("video/")
        guard draft.media.count < 10, !(video && !draft.media.isEmpty), !draft.media.contains(where: { $0["kind"].string == "video" }) else {
            throw ZovaFailure.server("Use one video or up to ten images per post.")
        }
        let epoch = authority
        var converted: URL?
        if ["image/heic", "image/heif", "image/heic-sequence", "image/heif-sequence"].contains(mime) {
            converted = try await Task.detached(priority: .userInitiated) { try NativeMediaFiles.compatibleImage(url) }.value
        }
        defer { NativeMediaFiles.remove(converted) }
        guard epoch == authority, !Task.isCancelled else { throw CancellationError() }
        let response = try await api.upload(file: converted ?? url, name: converted == nil ? name : (name as NSString).deletingPathExtension + ".jpg", mime: converted == nil ? mime : "image/jpeg", brand: brand)
        guard epoch == authority else { throw CancellationError() }
        let media = draft.media + response["assets"].array
        draft.workspace["media"] = .array(media); draft.workspace["media_asset_ids"] = .array(media.map { $0["id"] })
        if video {
            // Match Studio: video destinations currently support Instagram/TikTok.
            draft.selected = draft.selected.filter { ["instagram", "tiktok"].contains($0) }
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
    func assetFile(_ asset: JSONValue) async throws -> URL {
        let epoch = authority
        let url = try await api.downloadAsset(asset["id"].int, filename: asset["filename"].string, brand: brand)
        guard epoch == authority, !Task.isCancelled else { NativeMediaFiles.remove(url); throw CancellationError() }
        return url
    }
    func refreshResults(attempt: Int = 0) async throws {
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
        if pending && attempt < 40 {
            polling = Task { [weak self] in
                do { try await Task.sleep(for: .seconds(15)); guard let self, self.draft.id == id else { return }; try await self.refreshResults(attempt: attempt + 1) }
                catch { if !(error is CancellationError) { self?.handle(error) } }
            }
        }
    }
    func clear(preserveRecovery: Bool = false) {
        authority += 1; autosave?.cancel(); polling?.cancel()
        if preserveRecovery { if dirty { persistRecovery() } }
        else { NativeDraftRecovery.removeUser(account["profile"]["id"].int) }
        NativeMediaFiles.clear(); recovery = .null
        changeSerial = 0; savedSerial = 0; pendingReview = false; showReview = false
        draft = ProductDraft(); drafts = []; schedules = []; series = []; account = .null; results = .null; mediaNotice = ""
        brand = 0; selectedTab = 0; draftOffset = 0; moreDrafts = false
        accountSection = ""
        needsConsent = false; showIntro = false; reviewMode = "publish"; error = nil; saveStatus = "Ready"
    }
    private var recoveryOwner: String { "\(account["profile"]["id"].int):\(brand)" }
    private func persistRecovery() {
        guard account["profile"]["id"].int > 0 else { return }
        do { try NativeDraftRecovery.save(draft, owner: recoveryOwner) }
        catch { saveStatus = "Unsaved changes" }
    }
    func restoreRecovery(asNew: Bool = false) async throws {
        guard !recovery.isNull else { return }
        var restored = ProductDraft(recovery)
        let originalID = restored.id
        if asNew { restored.id = nil; restored.revision = 0; restored.status = "draft" }
        else if let id = restored.id {
            let current = ProductDraft(try await request("/api/drafts/\(id)"))
            guard current.editable, current.revision == restored.revision else {
                throw ZovaFailure.server("This post changed elsewhere. Use Save as new draft to keep both versions.")
            }
        }
        if draft.id != originalID && dirty { try await save() }
        draft = restored; changeSerial += 1; recovery = .null; persistRecovery(); try await save()
    }
    func savedVersion() async throws -> ProductDraft {
        guard let id = draft.id ?? (recovery["id"].int > 0 ? recovery["id"].int : nil) else { throw ZovaFailure.server("This idea has not been saved to your account yet.") }
        return ProductDraft(try await request("/api/drafts/\(id)"))
    }
    func useSavedVersion(_ saved: ProductDraft) {
        autosave?.cancel(); draft = saved; changeSerial = 0; savedSerial = 0
        discardRecovery(); saveStatus = "Saved"; results = .null
    }
    func discardRecovery() { NativeDraftRecovery.remove(owner: recoveryOwner); recovery = .null }
}
