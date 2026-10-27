import SwiftUI

struct NativePostOptionsView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    @State private var music = false
    @State private var export: URL?
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            NativeSheetHeader(title: "Post options")
            if store.draft.selected.contains("instagram") {
                Picker("Instagram format", selection: Binding(get: { store.draft.workspace["instagram_format"].string.isEmpty ? "post" : store.draft.workspace["instagram_format"].string }, set: { store.draft.workspace["instagram_format"] = .string($0); store.draft.workspace["instagram_audio"] = .null; store.changed() })) { Text("Post / Reel").tag("post"); Text("Story").tag("story") }.pickerStyle(.segmented)
                if store.draft.workspace["instagram_format"].string == "story" { Text("Only your photo or video appears in the Story. Caption, links and music are not added automatically.").font(.caption).foregroundStyle(.secondary) }
                Button(store.draft.workspace["instagram_audio"].isNull ? "Add Instagram music" : "Music · " + store.draft.workspace["instagram_audio"]["title"].string) { music = true }
            }
            if store.draft.selected.contains("x") {
                Picker("X thread", selection: Binding(get: { store.draft.threadLength }, set: { store.draft.threadLength = $0; store.changed() })) { Text("1 post").tag(1); Text("3 posts").tag(3); Text("5 posts").tag(5) }.pickerStyle(.segmented)
            }
            NativeField(title: "Source link", text: Binding(get: { store.draft.workspace["link_url"].string }, set: { store.draft.workspace["link_url"] = .string($0); store.changed() }), prompt: "https://…", lines: 1)
            NativeField(title: "Writing instructions", text: Binding(get: { store.draft.instruction }, set: { store.draft.instruction = String($0.prefix(5000)); store.changed() }), prompt: "Anything Zova should keep in mind", lines: 2)
            ForEach(store.draft.media, id: \.["id"].int) { asset in
                ZovaCard {
                    NativeAssetPreview(asset: asset)
                    HStack {
                        Button("Save / share media") { run {
                            let bytes = try await store.api.media("/media/download/\(asset["id"].int)", brand: store.brand)
                            let ext = (asset["filename"].string as NSString).pathExtension
                            let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + "." + (ext.isEmpty ? asset["kind"].string == "video" ? "mp4" : "jpg" : ext))
                            try bytes.write(to: url, options: [.atomic, .completeFileProtection]); export = url
                        } }
                        Spacer(); Button("Remove", role: .destructive) { store.removeMedia(asset["id"].int) }
                    }
                }
            }
            Button("Done") { run { try await store.save(); dismiss() } }.buttonStyle(ZovaPrimary())
        }.padding(22).disabled(store.busy) }.preferredColorScheme(.light)
            .sheet(isPresented: $music) { NativeMusicView().environmentObject(store) }
            .sheet(isPresented: Binding(get: { export != nil }, set: { if !$0 { cleanExport() } })) { if let export { NativeShare(items: [export]) } }
            .onDisappear { cleanExport() }
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
    private func cleanExport() { if let export { try? FileManager.default.removeItem(at: export) }; export = nil }
}

struct NativeShare: UIViewControllerRepresentable {
    let items: [Any]
    func makeUIViewController(context: Context) -> UIActivityViewController { UIActivityViewController(activityItems: items, applicationActivities: nil) }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) { }
}

struct NativeMusicView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    @State private var query = ""
    @State private var result: JSONValue = .null
    @State private var account = 0
    private var eligibleFormat: Bool { store.draft.workspace["instagram_format"].string != "story" && store.draft.media.count == 1 && store.draft.media[0]["kind"].string == "video" }
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            NativeSheetHeader(title: "Instagram music")
            if eligibleFormat {
                HStack { TextField("Search music", text: $query).textFieldStyle(.roundedBorder).onSubmit { search() }; Button("Search") { search() } }
                if result["accounts"].array.count > 1 {
                    Picker("Instagram account", selection: $account) { ForEach(result["accounts"].array, id: \.["id"].int) { row in Text(row["name"].string).tag(row["id"].int) } }.onChange(of: account) { old, new in if old != 0 && old != new { store.draft.workspace["instagram_audio"] = .null; store.changed(); search() } }
                }
                if store.busy { ProgressView("Checking music…") }
                Text(result["reason"].string).font(.callout).foregroundStyle(.secondary)
                ForEach(result["tracks"].array, id: \.["audio_id"].string) { track in
                    HStack {
                        Button {
                            store.draft.workspace["instagram_audio"] = .object(["audio_id": track["audio_id"], "title": track["title"], "artist": track["artist"], "connection_id": .integer(account), "audio_volume": .integer(100), "video_volume": .integer(100)])
                            store.changed()
                        } label: { VStack(alignment: .leading, spacing: 5) { Text(track["title"].string).font(.headline); Text(track["artist"].string).font(.caption).foregroundStyle(.secondary) }.frame(maxWidth: .infinity, alignment: .leading) }
                        if let url = ProductLinks.external(track["preview_url"].string) { Link("Listen ↗", destination: url).font(.caption) }
                    }.padding(14).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 12))
                }
            } else {
                Text("Add music to photos and Stories in Instagram. Save the media from Post options, then choose your music in Instagram.")
                if store.draft.workspace["instagram_format"].string != "story" { Button("Copy caption") { UIPasteboard.general.string = store.draft.variants["instagram"]["posts"].strings.joined(separator: "\n\n") } }
            }
            if !store.draft.workspace["instagram_audio"].isNull {
                Text("Selected: " + store.draft.workspace["instagram_audio"]["title"].string).font(.headline)
                ForEach([("Music volume", "audio_volume"), ("Original audio volume", "video_volume")], id: \.1) { title, key in
                    VStack(alignment: .leading) { Text(title + " · \(store.draft.workspace["instagram_audio"][key].int)%").font(.callout); Slider(value: Binding(get: { Double(store.draft.workspace["instagram_audio"][key].int) }, set: { store.draft.workspace["instagram_audio"][key] = .integer(Int($0)); store.changed() }), in: 1...100, step: 1) }
                }
                Button("Remove music") { store.draft.workspace["instagram_audio"] = .null; store.changed() }
            }
            Button("Done") { Task { await store.perform { try await store.save(); dismiss() } } }.buttonStyle(ZovaPrimary())
        }.padding(22) }.preferredColorScheme(.light).task { if eligibleFormat { search() } }
    }
    private func search() { Task { await store.perform {
        let path = "/api/instagram/audio?q=" + ProductLinks.query(query) + (account > 0 ? "&connection_id=\(account)" : "")
        result = try await store.request(path); account = result["connection_id"].int
    } } }
}
