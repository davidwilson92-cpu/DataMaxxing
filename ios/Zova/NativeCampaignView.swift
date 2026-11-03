import SwiftUI
import UniformTypeIdentifiers
import PhotosUI

struct NativeCampaignView: View {
    var initialCampaignID: Int? = nil
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) private var dismiss
    @State private var campaigns: [JSONValue] = []
    @State private var current = JSONValue.null
    @State private var idea = ""
    @State private var feedback = ""
    @State private var platforms: Set<String> = []
    @State private var start = Date().addingTimeInterval(86400)
    @State private var frequency = "daily"
    @State private var count = 4
    @State private var media: [JSONValue] = []
    @State private var importing = false
    @State private var photos: [PhotosPickerItem] = []
    @State private var working = false
    @State private var ready = false
    @State private var consent = false
    @State private var locked = false
    @State private var message = ""

    var body: some View {
        NavigationStack {
            Form {
                if locked {
                    Section("Premium") {
                        Text("Plan a series of posts with Premium.")
                        Link("Request Premium access", destination: URL(string: "mailto:support@zova-social.com?subject=Premium%20campaign%20access")!)
                    }
                } else if ready {
                    if current.isNull {
                        if !campaigns.isEmpty {
                            Section("Saved campaigns") {
                                ForEach(campaigns, id: \.["id"].int) { item in
                                    Button(String(item["brief"]["idea"].string.prefix(80))) {
                                        Task { await perform { try await reopen(item["id"].int) } }
                                    }.accessibilityIdentifier("saved-campaign-\(item["id"].int)")
                                }
                            }
                        }
                    } else {
                        Button("All campaigns") { current = .null; feedback = ""; message = "" }
                    }
                    if current.isNull { brief } else { review }
                }
                if working { ProgressView() }
                if !message.isEmpty { Text(message).foregroundStyle(.secondary) }
            }
            .buttonStyle(.borderless)
            .disabled(working)
            .navigationTitle(current.isNull ? "Campaigns" : String(current["brief"]["idea"].string.prefix(65)))
            .sheet(isPresented: $consent) { NativeAIConsentView().environmentObject(store) }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button(initialCampaignID == nil ? "Studio" : "Performance") { dismiss() }.disabled(working).accessibilityIdentifier("close-campaign") }
            }
            .interactiveDismissDisabled(working)
            .task { await perform {
                campaigns = try await store.request("/api/campaigns").array
                if let id = initialCampaignID { try await reopen(id) }
                ready = true
            } }
            .fileImporter(isPresented: $importing, allowedContentTypes: [.image, .movie], allowsMultipleSelection: true) { result in
                if case .success(let files) = result { Task { await perform { try await upload(files) } } }
            }
        }
    }
    @ViewBuilder private var brief: some View {
        Section("What are you promoting?") { TextEditor(text: $idea).frame(minHeight: 72) }
        Section("Photos and videos") {
            ForEach(media, id: \.["id"].int) { asset in Text(asset["filename"].string) }
            if media.count < 10 {
                PhotosPicker(selection: $photos, maxSelectionCount: 10 - media.count, matching: .any(of: [.images, .videos])) {
                    Label("Photos and videos", systemImage: "photo.on.rectangle")
                }
                .onChange(of: photos) { _, items in
                    guard !items.isEmpty else { return }
                    Task { await perform {
                        defer { photos = [] }
                        for item in items {
                            guard let picked = try await item.loadTransferable(type: PickedMedia.self) else {
                                throw ZovaFailure.server("This file could not be opened.")
                            }
                            defer { NativeMediaFiles.remove(picked.url) }
                            try await upload([picked.url])
                        }
                    } }
                }
                Button("Browse files") { importing = true }
            }
        }
        Section("Platforms") {
            ForEach(SocialPlatform.allCases) { p in
                Toggle(p.title, isOn: Binding(get: { platforms.contains(p.rawValue) }, set: { selected in
                    if selected { platforms.insert(p.rawValue) } else { platforms.remove(p.rawValue) }
                }))
            }
        }
        Section {
            DatePicker("First post", selection: $start, in: Date()...)
            Picker("Frequency", selection: $frequency) { Text("Daily").tag("daily"); Text("Weekly").tag("weekly") }
            Stepper("\(count) posts", value: $count, in: 1...10)
        }
        Button("Build campaign") { Task { await perform { try await build() } } }
            .disabled(idea.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || platforms.isEmpty || count < platforms.count)
    }
    @ViewBuilder private var review: some View {
        Section {
            ForEach(Array(current["posts"].array.enumerated()), id: \.offset) { index, post in
                VStack(alignment: .leading, spacing: 6) {
                    Text(SocialPlatform(rawValue: post["platform"].string)?.title ?? post["platform"].string).font(.headline)
                    if index < current["dates"].array.count {
                        Text(ProductLinks.displayDate(ProductLinks.date(current["dates"].array[index]["utc"].string) ?? start, timezone: current["brief"]["timezone"].string)).font(.caption)
                    }
                    Text(post["caption"].string)
                    if let asset = current["assets"].array.first(where: { $0["id"] == post["asset_id"] }) {
                        Text(asset["name"].string).font(.caption)
                    }
                    if current["draft_ids"].array.isEmpty || post["editable"].bool {
                        CampaignPostEditor(row: current, index: index, errorMessage: message, working: working) { body in
                            await perform {
                                select(try await store.request("/api/campaigns/\(current["id"].int)/posts/\(index)", method: "POST", body: body))
                            }
                        }.id("\(current["id"].int)-\(current["revision"].int)-\(post["draft_revision"].int)-\(index)")
                    }
                    if !post["status"].string.isEmpty { Text(post["status"].string.capitalized).font(.caption) }
                    if !post["schedule"].isNull, index < current["dates"].array.count {
                        CampaignTimeEditor(when: current["dates"].array[index]["utc"].string, zone: current["brief"]["timezone"].string) { local in
                            await perform {
                                _ = try await store.request("/api/schedules/\(post["schedule"]["id"].int)/reschedule", method: "POST",
                                    body: .object(["scheduled_local":.string(local), "timezone":current["brief"]["timezone"],
                                                   "expected_updated_at":post["schedule"]["updated_at"]]))
                                try await reopen(current["id"].int)
                            }
                        }.id(post["schedule"]["updated_at"].string)
                    }
                    if post["status"].string == "scheduled" {
                        Button("Unschedule to edit") { Task { await perform {
                            _ = try await store.request("/api/schedules/drafts/\(current["draft_ids"].array[index].int)/edit", method: "POST", body: .object(["revision":post["draft_revision"]]))
                            try await reopen(current["id"].int)
                        } } }
                    }
                    if index < current["draft_ids"].array.count && post["status"].string != "removed" {
                        Button("Open in Studio") {
                            Task { await perform { if store.dirty { try await store.save() }; try await store.openDraft(current["draft_ids"].array[index].int); store.selectedTab = 0; dismiss() } }
                        }
                    }
                }
            }
        }
        if current["draft_ids"].array.isEmpty {
            Section("What would you change?") {
                TextField("Your feedback", text: $feedback, axis: .vertical)
                Button(current["posts"].array.isEmpty ? "Generate plan" : "Update plan") { Task { await perform { try await generate() } } }
            }
            if !current["posts"].array.isEmpty {
                Button("Save posts to Schedule") {
                    Task { await perform {
                        select(try await store.request("/api/campaigns/\(current["id"].int)/accept", method: "POST", body: .object(["revision": current["revision"]])))
                        try await reopen(current["id"].int)
                        message = "Drafts saved. Review each post before publishing."
                    } }
                }
            }
        }
    }
    private func reopen(_ id: Int) async throws {
        select(try await store.request("/api/campaigns/\(id)"))
    }
    private func select(_ row: JSONValue) {
        current = row; feedback = row["feedback"].string
        campaigns.removeAll { $0["id"] == row["id"] }; campaigns.insert(row, at: 0)
    }
    private func upload(_ files: [URL]) async throws {
        guard media.count + files.count <= 10 else { throw ZovaFailure.server("Choose up to ten files.") }
        for url in files {
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            let mime = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
            let result = try await store.api.upload(file: url, name: url.lastPathComponent, mime: mime, brand: store.brand)
            media.append(contentsOf: result["assets"].array)
        }
    }
    private func build() async throws {
        let date = DateFormatter()
        date.locale = Locale(identifier: "en_US_POSIX"); date.timeZone = .current; date.dateFormat = "yyyy-MM-dd'T'HH:mm"
        let body: JSONValue = .object(["idea": .string(idea), "platforms": .strings(platforms.sorted()), "media": .array(media.map { $0["id"] }),
                                      "start": .string(date.string(from: start)), "timezone": .string(TimeZone.current.identifier),
                                      "frequency": .string(frequency), "count": .integer(count)])
        select(try await store.request("/api/campaigns", method: "POST", body: body))
        idea = ""; media = []; try await generate()
    }
    private func generate() async throws {
        select(try await store.request("/api/ai/campaigns/\(current["id"].int)/plan", method: "POST",
                                       body: .object(["revision": current["revision"], "feedback": .string(feedback)])))
    }
    @MainActor private func perform(_ work: () async throws -> Void) async {
        guard !working else { return }; working = true; message = ""
        defer { working = false }
        do { try await work() }
        catch let error as ProductError where error.status == 402 && !ready { locked = true }
        catch let error as ProductError where error.code == "ai_permission_required" {
            message = "Your campaign is saved. Allow AI sharing, then generate your plan."; consent = true
        }
        catch { message = error.localizedDescription; if case ZovaFailure.signInRequired = error { store.signedOut = true } }
    }
}
