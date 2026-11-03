import SwiftUI
import UniformTypeIdentifiers
import PhotosUI

struct StudioModePicker: View {
    @Binding var campaign: Bool

    var body: some View {
        Picker("Studio mode", selection: $campaign) {
            Text("Posts").tag(false)
            Text("Campaign").tag(true)
        }
        .pickerStyle(.segmented)
        .frame(maxWidth: 220, minHeight: 44)
    }
}

struct NativeCampaignView: View {
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
                    Menu(current.isNull ? "New campaign" : "Saved campaigns") {
                        Button("New campaign") { current = .null; feedback = "" }
                        ForEach(campaigns, id: \.["id"].int) { item in
                            Button(item["brief"]["idea"].string) { select(item) }
                        }
                    }
                    if current.isNull { brief } else { review }
                }
                if working { ProgressView() }
                if !message.isEmpty { Text(message).foregroundStyle(.secondary) }
            }
            .disabled(working)
            .navigationTitle("Campaigns")
            .sheet(isPresented: $consent) { NativeAIConsentView().environmentObject(store) }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    StudioModePicker(campaign: Binding(get: { true }, set: { if !$0 { dismiss() } })).disabled(working)
                }
            }
            .interactiveDismissDisabled(working)
            .task { await perform { campaigns = try await store.request("/api/campaigns").array; ready = true } }
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
        Section(current["brief"]["idea"].string) {
            ForEach(Array(current["posts"].array.enumerated()), id: \.offset) { index, post in
                VStack(alignment: .leading, spacing: 6) {
                    Text(SocialPlatform(rawValue: post["platform"].string)?.title ?? post["platform"].string).font(.headline)
                    if index < current["dates"].array.count {
                        Text(current["dates"].array[index]["local"].string).font(.caption)
                    }
                    Text(post["caption"].string)
                    if let asset = current["assets"].array.first(where: { $0["id"] == post["asset_id"] }) {
                        Text(asset["name"].string).font(.caption)
                    }
                    if index < current["draft_ids"].array.count {
                        Button("Open draft") {
                            Task { await perform { if store.dirty { try await store.save() }; try await store.openDraft(current["draft_ids"].array[index].int); dismiss() } }
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
                        message = "Drafts saved. Review each post before publishing."
                    } }
                }
            }
        }
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
