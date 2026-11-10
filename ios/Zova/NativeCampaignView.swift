import SwiftUI
import UniformTypeIdentifiers
import PhotosUI

struct NativeCampaignView: View {
    var initialCampaignID: Int? = nil
    var embedded = false
    @State private var failedFiles: [URL] = []
    @State private var failedPhotos: [PhotosPickerItem] = []
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) private var dismiss
    @StateObject private var writer = CampaignBriefWriter()
    @State private var briefZone = TimeZone.current.identifier
    @State private var campaigns: [JSONValue] = []
    @State private var current = JSONValue.null
    @State private var name = ""
    @State private var idea = ""
    @State private var suggested = true
    @State private var sortBy = "Date"
    @State private var calendarView = false
    @State private var selectedDay = ""
    @State private var renaming = false
    @State private var newName = ""
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
            Group {
            if !current.isNull && ready && !locked {
                ScrollView {
                    VStack(alignment:.leading,spacing:12) {
                        review
                        if working { ProgressView() }
                        if !message.isEmpty { Text(message).foregroundStyle(.secondary) }
                    }.padding(.horizontal,16).padding(.vertical,8)
                }
            } else {
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
                                    Button(campaignName(item)) {
                                        Task { await perform { try await reopen(item["id"].int) } }
                                    }.accessibilityIdentifier("saved-campaign-\(item["id"].int)")
                                }
                            }
                        }
                    }
                    brief
                }
                if working { ProgressView() }
                if !message.isEmpty { Text(message).foregroundStyle(.secondary) }
            }
            .scrollContentBackground(.hidden)
            }
            }
            .background(Color.black).preferredColorScheme(.dark).tint(.white)
            .buttonStyle(.borderless)
            .disabled(working)
            .navigationTitle(current.isNull ? "Campaigns" : campaignName(current))
            .alert("Campaign name", isPresented:$renaming) {
                TextField("Name",text:$newName)
                Button("Cancel",role:.cancel) {}
                Button("Save") {Task {await perform {
                    select(try await store.request("/api/campaigns/\(current["id"].int)/name",method:"POST",body:.object(["revision":current["revision"],"name":.string(newName)])))
                }}}
            }
            .sheet(isPresented: $consent) { NativeAIConsentView().environmentObject(store) }
            .navigationBarTitleDisplayMode(.inline)
            .toolbarBackground(Color.black,for:.navigationBar)
            .toolbarBackground(.visible,for:.navigationBar)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button {
                    if embedded {store.selectedTab = 0; return}
                    Task { await perform {
                        if ready && current.isNull { try await writer.save(briefPayload,store:store) }
                        if embedded { store.selectedTab = 0 } else { dismiss() }
                    } }
                } label: { Image(systemName:"xmark").frame(minWidth:44,minHeight:44) }.accessibilityLabel("Close campaign").accessibilityIdentifier("close-campaign") }
            }
            .interactiveDismissDisabled(working && !embedded)
            .task { await perform {
                campaigns = try await store.request("/api/campaigns").array
                let saved = try await store.request("/api/campaign-brief")
                let partial = saved["brief"]
                if !partial.isNull {
                    suggested = partial["recommend_times"].bool
                    name = partial["name"].string; idea = partial["idea"].string; platforms = Set(partial["platforms"].strings)
                    briefZone = partial["timezone"].string; frequency = partial["frequency"].string
                    count = max(1,partial["count"].int); media = partial["assets"].array
                    if let date = dateFormatter.date(from: partial["start"].string) { start = date }
                }
                writer.restore(briefPayload, revision: saved["revision"].int, restored: !partial.isNull)
                if let id = initialCampaignID { try await reopen(id) }
                ready = true
            } }
            .onChange(of: briefPayload) { _, next in
                if ready && current.isNull { Task { try? await writer.save(next,store:store) } }
            }
            .fileImporter(isPresented: $importing, allowedContentTypes: [.image, .movie], allowsMultipleSelection: true) { result in
                if case .success(let files) = result { Task { await perform { await uploadFiles(files) } } }
            }
        }
    }
    @ViewBuilder private var brief: some View {
        Section("Campaign name") { TextField("Summer launch",text:$name).textFieldStyle(.roundedBorder).accessibilityLabel("Campaign name") }
        Section("What are you promoting?") { TextEditor(text: $idea).frame(minHeight: 120).padding(8).overlay(RoundedRectangle(cornerRadius:10).stroke(Color.gray.opacity(0.45))).accessibilityLabel("Campaign brief") }
        Section("Photos and videos") {
            ForEach(media, id: \.["id"].int) { asset in
                HStack { CampaignMediaTile(asset:asset,height:64).frame(width:64,height:64).clipped(); Text(asset["filename"].string).font(.caption).lineLimit(2); Spacer(); Button {media.removeAll {$0["id"]==asset["id"]}} label:{Image(systemName:"xmark.circle")}.accessibilityLabel("Remove "+asset["filename"].string) }
            }
            if !failedFiles.isEmpty {Button("Retry files") {Task {await perform {await uploadFiles(failedFiles)}}}}
            if !failedPhotos.isEmpty {Button("Retry remaining files") {Task {await perform {await uploadPhotos(failedPhotos)}}}}
            if media.count < 10 {
                PhotosPicker(selection: $photos, maxSelectionCount: 10 - media.count, matching: .any(of: [.images, .videos])) {
                    Label("Photos and videos", systemImage: "photo.on.rectangle")
                }
                .onChange(of: photos) { _, items in
                    guard !items.isEmpty else { return }
                    Task { await perform {
                        defer { photos = [] }
                        await uploadPhotos(items)
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
            Picker("Timing", selection:$suggested) { Text("Zova’s suggested times").tag(true);Text("Choose my time").tag(false) }
            DatePicker("First post", selection: $start, in: Date()..., displayedComponents:suggested ? [.date] : [.date,.hourAndMinute]).environment(\.timeZone, dateFormatter.timeZone)
            Picker("Frequency", selection: $frequency) { Text("Daily").tag("daily"); Text("Weekly").tag("weekly") }
            Stepper("\(count) posts", value: $count, in: 1...10)
        }
        if !writer.note.isEmpty { Text(writer.note).font(.caption).foregroundStyle(.secondary) }
        Button("Build campaign") { Task { await perform { try await build() } } }
            .disabled(name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || name.count > 80 || idea.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || platforms.isEmpty || count < platforms.count)
    }
    private var positions: [Int] {
        let posts=current["posts"].array, dates=current["dates"].array
        func key(_ i:Int)->String {
            if sortBy=="Platform"{return posts[i]["platform"].string}
            if sortBy=="Media type"{return campaignAssets(current,posts[i]).first?["kind"].string ?? "text"}
            return ""
        }
        return posts.indices.filter { !calendarView || dates[$0]["local"].string.hasPrefix(selectedDay) }
            .sorted { (key($0), dates[$0]["local"].string,$0) < (key($1),dates[$1]["local"].string,$1) }
    }
    @ViewBuilder private var review: some View {
        CampaignActionsView(row:current,working:working,calendarView:$calendarView,sortBy:$sortBy,
        allCampaigns:{current = .null; feedback = ""; message = ""},
        rename:{newName=campaignName(current);renaming=true},refresh:{
            await perform {try await reopen(current["id"].int)}
        },request:{path,body in
            var succeeded=false
            await perform {
                select(try await store.request(path,method:"POST",body:body))
                message="Saved. Nothing has been published."
                succeeded=true
            }
            return succeeded
        }).id(current["id"].int)
            if calendarView {
                CampaignCalendar(days:current["dates"].array.map {String($0["local"].string.prefix(10))},platforms:current["posts"].array.map {$0["platform"].string},selected:$selectedDay)
                    .id(current["id"].int)
            }
        LazyVStack(alignment:.leading,spacing:16) {
            ForEach(positions, id: \.self) { index in
                let post=current["posts"].array[index]
                VStack(alignment: .leading, spacing: 6) {
                    let slot=current["dates"].array[index],zone=current["brief"]["timezone"].string
                    CampaignStrip(platform:post["platform"].string,date:ProductLinks.displayDate(ProductLinks.date(slot["utc"].string) ?? start,timezone:zone)+" · "+zone)
                    ForEach(campaignAssets(current,post),id:\.["id"].int){asset in CampaignMediaTile(asset:asset)}
                    Text(post["caption"].string)
                    if !post["timing_warning"].string.isEmpty {
                        Label(post["timing_warning"].string, systemImage: "calendar.badge.exclamationmark").font(.callout)
                    }
                    if !slot["reason"].string.isEmpty {Text(slot["reason"].string).font(.caption).foregroundStyle(.secondary)}
                    HStack(spacing:8) {
                    if current["draft_ids"].array.isEmpty || post["editable"].bool {
                        CampaignPostEditor(row: current, index: index, errorMessage: message, working: working) { body in
                            await perform {
                                select(try await store.request("/api/campaigns/\(current["id"].int)/posts/\(index)", method: "POST", body: body))
                            }
                        }.id("\(current["id"].int)-\(current["revision"].int)-\(post["draft_revision"].int)-\(index)")
                    }
                    if !post["status"].string.isEmpty { Text(post["status"].string.capitalized).font(.caption).foregroundStyle(.secondary) }
                        Spacer(minLength:0)
                    if index < current["draft_ids"].array.count && post["status"].string != "removed" {
                        Button("Open in Studio") {
                            Task { await perform { if store.dirty { try await store.save() }; try await store.openDraft(current["draft_ids"].array[index].int); store.selectedTab = 0; dismiss() } }
                        }
                    }
                    }.font(.subheadline).buttonStyle(.borderless)
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
                }.padding(12).background(Color(white:0.075),in:RoundedRectangle(cornerRadius:14))
                    .overlay(RoundedRectangle(cornerRadius:14).stroke(Color.white.opacity(0.16)))
                    .accessibilityIdentifier("campaign-post-\(index)")
            }
        }
        if current["draft_ids"].array.isEmpty {
            if current["posts"].array.isEmpty {
            Section("What would you change?") {
                TextField("Your feedback", text: $feedback, axis: .vertical)
                Button(current["posts"].array.isEmpty ? "Generate plan" : "Update plan") { Task { await perform { try await generate() } } }
            }
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
        if current["id"] != row["id"] || selectedDay.isEmpty {
            selectedDay=String((row["dates"].array.map { $0["local"].string }.min() ?? "").prefix(10))
        }
        current = row; feedback = row["feedback"].string
        campaigns.removeAll { $0["id"] == row["id"] }; campaigns.insert(row, at: 0)
    }
    private func uploadFiles(_ files:[URL]) async {
        let authority = store.authority
        failedFiles = []
        for file in files {
            guard authority == store.authority else { return }
            do {try await upload([file])}
            catch {failedFiles.append(file);message = "Some files could not upload. Retry files."}
        }
    }
    private func uploadPhotos(_ items:[PhotosPickerItem]) async {
        let authority = store.authority
        failedPhotos = []
        for item in items {
            guard authority == store.authority else { return }
            do {
                guard let picked = try await item.loadTransferable(type: PickedMedia.self) else { throw ZovaFailure.server("This file could not be opened.") }
                defer { NativeMediaFiles.remove(picked.url) }
                guard authority == store.authority else { return }
                try await upload([picked.url])
            } catch { failedPhotos.append(item); message = "Some files could not upload. Retry remaining files." }
        }
    }
    private func upload(_ files: [URL]) async throws {
        let authority = store.authority, brand = store.brand
        guard media.count + files.count <= 10 else { throw ZovaFailure.server("Choose up to ten files.") }
        for url in files {
            guard authority == store.authority else { throw CancellationError() }
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            let mime = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
            let result = try await store.api.upload(file: url, name: url.lastPathComponent, mime: mime, brand: brand)
            guard authority == store.authority else {throw CancellationError()}
            media.append(contentsOf: result["assets"].array)
            do {try await writer.save(briefPayload,store:store)} catch { message = "File uploaded. Brief save failed. "+error.localizedDescription }
        }
    }
    private var dateFormatter: DateFormatter {
        let date = DateFormatter()
        date.locale = Locale(identifier: "en_US_POSIX"); date.timeZone = TimeZone(identifier: briefZone) ?? .current; date.dateFormat = "yyyy-MM-dd'T'HH:mm"
        return date
    }
    private var briefPayload: JSONValue {
        let scheduled = dateFormatter.string(from:start)
        return .object(["name":.string(name),"recommend_times":.bool(suggested),"idea": .string(idea), "platforms": .strings(platforms.sorted()), "media": .array(media.map { $0["id"] }),
                                      "start": .string(suggested ? String(scheduled.prefix(10))+"T23:00" : scheduled), "timezone": .string(briefZone),
                                      "frequency": .string(frequency), "count": .integer(count)])
    }
    private func build() async throws {
        var body = briefPayload
        try await writer.save(body,store:store)
        body["brief_revision"] = .integer(writer.revision)
        select(try await store.request("/api/campaigns", method: "POST", body: body))
        name = ""; idea = ""; media = []; platforms = []; suggested = true; count = 4; frequency = "daily"
        briefZone = TimeZone.current.identifier; start = Date().addingTimeInterval(86400)
        writer.restore(briefPayload,revision:writer.revision+1,restored:false)
        try await generate()
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
