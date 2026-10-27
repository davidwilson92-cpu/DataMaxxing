import SwiftUI
import PhotosUI
import UniformTypeIdentifiers

struct PickedMedia: Transferable {
    let url: URL
    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(importedContentType: .movie) { received in
            let target = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + "." + (received.file.pathExtension.isEmpty ? "mov" : received.file.pathExtension))
            try FileManager.default.copyItem(at: received.file, to: target)
            try FileManager.default.setAttributes([.protectionKey: FileProtectionType.complete], ofItemAtPath: target.path)
            return PickedMedia(url: target)
        }
        FileRepresentation(importedContentType: .image) { received in
            let target = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + "." + (received.file.pathExtension.isEmpty ? "jpg" : received.file.pathExtension))
            try FileManager.default.copyItem(at: received.file, to: target)
            try FileManager.default.setAttributes([.protectionKey: FileProtectionType.complete], ofItemAtPath: target.path)
            return PickedMedia(url: target)
        }
    }
}

struct NativeStudioView: View {
    @EnvironmentObject var store: ProductStore
    @Binding var nextMove: Bool
    @Binding var strategy: Bool
    @FocusState private var focused: Bool
    @State private var history = false
    @State private var options = false
    @State private var importer = false
    @State private var camera = false
    @State private var picker: PhotosPickerItem?
    @State private var captionEditing = false
    var body: some View {
        VStack(spacing: 0) {
            header
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 22) {
                        if store.draft.conversation.isEmpty && store.draft.variants.object.isEmpty && !focused {
                            VStack(spacing: 18) {
                                Text("How can we grow your\nengagement today?").font(.system(size: 29, weight: .bold)).multilineTextAlignment(.center)
                                Text("Share your ideas. Zova’s AI helps shape them into a plan and posts in your voice.").foregroundStyle(.secondary).multilineTextAlignment(.center)
                                HStack { Button("Plan my socials") { strategy = true }; Button("Improve a caption") { store.draft.composer = "Improve this caption: "; store.changed(); focused = true } }.buttonStyle(.bordered)
                            }.padding(.top, 40).padding(.bottom, 25).frame(maxWidth: .infinity)
                        }
                        ForEach(Array(store.draft.conversation.enumerated()), id: \.offset) { _, message in
                            HStack {
                                if message["role"].string == "user" { Spacer(minLength: 24) }
                                VStack(alignment: .leading, spacing: 10) {
                                    Text(message["content"].string).textSelection(.enabled)
                                    let media = message["media"].array.isEmpty ? store.draft.media.filter { message["media_asset_ids"].array.contains($0["id"]) } : message["media"].array
                                    ForEach(media, id: \.["id"].int) { asset in NativeAssetPreview(asset: asset) }
                                }.padding(16).background(message["role"].string == "user" ? ZovaDesign.pale : .clear, in: RoundedRectangle(cornerRadius: 20))
                                if message["role"].string != "user" { Spacer(minLength: 24) }
                            }
                        }
                        if !store.draft.variants.object.isEmpty { caption }
                        if !store.draft.workspace["pending_message"].string.isEmpty && !store.busy {
                            Button("Retry this idea") { run { try await store.send(retry: true) } }.buttonStyle(.bordered)
                        }
                        if !store.results.isNull {
                            ZovaCard { NativeInlineStatus(value: store.results); Button("Refresh results") { run { try await store.refreshResults() } } }
                        }
                        if store.busy { HStack { ProgressView(); Text("Working…").font(.callout).foregroundStyle(.secondary) }.accessibilityIdentifier("studio-working") }
                        Color.clear.frame(height: 1).id("bottom")
                    }.padding(.horizontal, 18).padding(.vertical, 16)
                }.scrollDismissesKeyboard(.interactively)
                    .onChange(of: store.draft.conversation.count) { _, _ in withAnimation { proxy.scrollTo("bottom", anchor: .bottom) } }
                    .onChange(of: store.busy) { _, _ in if !focused { withAnimation { proxy.scrollTo("bottom", anchor: .bottom) } } }
            }
            if store.draft.editable { composer } else { Button("+ New post") { run { try await store.newPost() } }.buttonStyle(ZovaPrimary()).padding(18) }
        }.foregroundStyle(ZovaDesign.ink)
            .sheet(isPresented: $history) { NativeHistoryView().environmentObject(store) }
            .sheet(isPresented: $options) { NativePostOptionsView().environmentObject(store) }
            .fileImporter(isPresented: $importer, allowedContentTypes: [.image, .movie]) { result in
                switch result {
                case .success(let url):
                    run {
                        guard url.startAccessingSecurityScopedResource() else { throw ZovaFailure.server("Choose that file again to allow access.") }
                        defer { url.stopAccessingSecurityScopedResource() }
                        try await store.upload(url, name: url.lastPathComponent, mime: UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream")
                    }
                case .failure(let error): store.handle(error)
                }
            }
            .sheet(isPresented: $camera) { NativeCamera { url, mime in camera = false; run { defer { try? FileManager.default.removeItem(at: url) }; try await store.upload(url, name: url.lastPathComponent, mime: mime) } } }
            .onChange(of: picker) { _, item in
                guard let item else { return }
                run {
                    defer { picker = nil }
                    guard let media = try await item.loadTransferable(type: PickedMedia.self) else { throw ZovaFailure.server("This photo or video could not be opened.") }
                    defer { try? FileManager.default.removeItem(at: media.url) }
                    try await store.upload(media.url, name: media.url.lastPathComponent, mime: UTType(filenameExtension: media.url.pathExtension)?.preferredMIMEType ?? "application/octet-stream")
                }
            }
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
    private var header: some View {
        VStack(spacing: 5) {
            HStack(spacing: 10) {
                HStack(spacing: 5) { Image("ZovaMark").resizable().scaledToFit().frame(width: 24, height: 26); Text("Zova").font(.title3.bold()) }
                Spacer(minLength: 0)
                Button { focused = false; run { try await store.newPost() } } label: { Label("New post", systemImage: "plus").font(.caption.weight(.medium)).frame(minHeight: 44) }.disabled(store.busy).accessibilityIdentifier("new-post")
                Button { focused = false; nextMove = true } label: {
                    Label("Next move", systemImage: "sparkles").font(.subheadline.bold()).padding(.horizontal, 13).frame(height: 44).foregroundStyle(.white).background(ZovaDesign.hero, in: Capsule())
                }.accessibilityIdentifier("next-move").disabled(store.busy)
            }
            HStack {
                Menu {
                    ForEach(store.account["brand"]["choices"].array, id: \.["id"].int) { brand in
                        Button(brand["name"].string) { run { try await store.switchBrand(brand["id"].int) } }
                    }
                } label: { HStack(spacing: 5) { Text(store.account["brand"]["name"].string); Image(systemName: "chevron.down").font(.caption2) }.font(.caption).foregroundStyle(.secondary).frame(minHeight: 30) }.disabled(store.busy)
                Spacer()
                Button { history = true } label: { Image(systemName: "clock.arrow.circlepath").frame(width: 44, height: 34) }.accessibilityLabel("Your posts").disabled(store.busy)
            }
        }.padding(.horizontal, 18).padding(.top, 8).padding(.bottom, 4)
    }
    private var caption: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                ForEach(SocialPlatform.allCases.filter { store.draft.variants.object[$0.rawValue] != nil }) { platform in
                    Button { store.draft.active = platform.rawValue; store.changed() } label: {
                        NativePlatformMark(platform: platform.rawValue).frame(width: 44, height: 44).background(store.draft.active == platform.rawValue ? ZovaDesign.pale : .clear, in: RoundedRectangle(cornerRadius: 12))
                    }.accessibilityLabel("Edit " + platform.title + " caption")
                }
                Spacer()
                Button { UIPasteboard.general.string = store.draft.variants[store.draft.active]["posts"].strings.joined(separator: "\n\n") } label: { Image(systemName: "doc.on.doc").frame(width: 44, height: 44) }.accessibilityLabel("Copy caption")
                if !store.draft.workspace["text_history"].array.isEmpty {
                    Button { store.draft.undo(); store.changed() } label: { Image(systemName: "arrow.uturn.backward").frame(width: 44, height: 44) }.accessibilityLabel("Undo caption change")
                }
            }
            ForEach(Array(store.draft.variants[store.draft.active]["posts"].strings.enumerated()), id: \.offset) { index, _ in
                TextField("Edit caption", text: Binding(get: { store.caption(store.draft.active, index: index) }, set: { store.editCaption(store.draft.active, index: index, text: $0) }), axis: .vertical)
                    .lineLimit(4...20).padding(16).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 16))
                    .disabled(store.busy || !store.draft.editable).accessibilityIdentifier("caption-\(index)")
            }
            ForEach(store.draft.media, id: \.["id"].int) { NativeAssetPreview(asset: $0) }
            if store.draft.editable {
                HStack {
                    Button("Schedule") { focused = false; store.reviewMode = "schedule"; store.showReview = true }.buttonStyle(.bordered)
                    Button("Review post →") { focused = false; store.reviewMode = "publish"; store.showReview = true }.buttonStyle(ZovaPrimary())
                }.disabled(store.busy)
            }
        }
    }
    private var unsentMedia: [JSONValue] {
        let sent = store.draft.conversation.flatMap { $0["media_asset_ids"].array }
        return store.draft.media.filter { !sent.contains($0["id"]) }
    }
    private var composer: some View {
        VStack(spacing: 6) {
            VStack(alignment: .leading, spacing: 10) {
                if !unsentMedia.isEmpty {
                    ScrollView(.horizontal) { HStack { ForEach(unsentMedia, id: \.["id"].int) { asset in
                        HStack { NativeAssetPreview(asset: asset, compact: true); Button { store.removeMedia(asset["id"].int) } label: { Image(systemName: "xmark.circle.fill") }.accessibilityLabel("Remove " + asset["filename"].string) }.padding(5).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 12))
                    } } }
                }
                TextField("Start drafting your next post…", text: Binding(get: { store.draft.composer }, set: { store.draft.composer = String($0.prefix(12000)); store.changed() }), axis: .vertical)
                    .lineLimit(2...5).focused($focused).accessibilityIdentifier("post-composer").disabled(store.busy)
                HStack(spacing: 8) {
                    ForEach(SocialPlatform.allCases) { platform in
                        Button {
                            var selected = store.draft.selected
                            if selected.contains(platform.rawValue) { selected.removeAll { $0 == platform.rawValue } } else { selected.append(platform.rawValue) }
                            store.draft.selected = selected; store.changed()
                        } label: { NativePlatformMark(platform: platform.rawValue, size: 27).frame(width: 44, height: 44).background(store.draft.selected.contains(platform.rawValue) ? ZovaDesign.pale : Color.gray.opacity(0.06), in: RoundedRectangle(cornerRadius: 12)).overlay(RoundedRectangle(cornerRadius: 12).stroke(store.draft.selected.contains(platform.rawValue) ? ZovaDesign.purple : .clear)) }
                            .accessibilityLabel(platform.title).accessibilityValue(store.draft.selected.contains(platform.rawValue) ? "Selected" : "Not selected").disabled(store.busy)
                    }
                    Spacer(minLength: 0)
                }
                HStack {
                    Menu {
                        PhotosPicker(selection: $picker, matching: .any(of: [.images, .videos])) { Label("Photo library", systemImage: "photo") }
                        Button("Choose file", systemImage: "folder") { importer = true }
                        if UIImagePickerController.isSourceTypeAvailable(.camera) { Button("Camera", systemImage: "camera") { camera = true } }
                    } label: { Image(systemName: "plus").font(.title3).frame(width: 44, height: 44) }.accessibilityLabel("Add attachment").disabled(store.busy)
                    Button("Post options") { focused = false; options = true }.font(.subheadline).frame(minHeight: 44).disabled(store.busy)
                    Spacer()
                    Button { focused = false; run { try await store.send() } } label: { Image(systemName: "arrow.up").font(.title2.bold()).foregroundStyle(.white).frame(width: 48, height: 48).background(ZovaDesign.purple.opacity(store.draft.composer.isEmpty ? 0.4 : 1), in: Circle()) }.accessibilityLabel("Send idea").disabled(store.busy || store.draft.composer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }.padding(14).background(Color.white, in: RoundedRectangle(cornerRadius: 22)).overlay(RoundedRectangle(cornerRadius: 22).stroke(focused ? ZovaDesign.purple : ZovaDesign.line)).padding(.horizontal, 14)
            if !focused { HStack { Text(store.saveStatus); Spacer(); Text("Nothing posts without your approval.") }.font(.system(size: 10)).foregroundStyle(.secondary).padding(.horizontal, 18) }
        }.padding(.bottom, 8)
    }
}

struct NativeHistoryView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    @State private var query = ""
    var body: some View {
        NavigationStack {
            List(store.drafts, id: \.["id"].int) { row in
                Button { Task { await store.perform { try await store.openDraft(row["id"].int); dismiss() } } } label: {
                    VStack(alignment: .leading, spacing: 6) { Text(row["title"].string).foregroundStyle(.primary); Text(row["status"].string.capitalized).font(.caption).foregroundStyle(.secondary) }
                }
            }.navigationTitle("Your posts").searchable(text: $query)
                .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
                .task { await load() }.onSubmit(of: .search) { Task { await load() } }
        }
    }
    private func load() async { await store.perform { store.drafts = try await store.request("/api/drafts?q=" + ProductLinks.query(query)).array } }
}

struct NativeCamera: UIViewControllerRepresentable {
    let selected: (URL, String) -> Void
    @Environment(\.dismiss) var dismiss
    func makeCoordinator() -> Coordinator { Coordinator(self) }
    func makeUIViewController(context: Context) -> UIImagePickerController {
        let picker = UIImagePickerController(); picker.sourceType = .camera
        picker.mediaTypes = [UTType.image.identifier, UTType.movie.identifier]; picker.videoQuality = .typeHigh
        picker.delegate = context.coordinator; return picker
    }
    func updateUIViewController(_ uiViewController: UIImagePickerController, context: Context) { }
    final class Coordinator: NSObject, UINavigationControllerDelegate, UIImagePickerControllerDelegate {
        let parent: NativeCamera
        init(_ parent: NativeCamera) { self.parent = parent }
        func imagePickerControllerDidCancel(_ picker: UIImagePickerController) { parent.dismiss() }
        func imagePickerController(_ picker: UIImagePickerController, didFinishPickingMediaWithInfo info: [UIImagePickerController.InfoKey: Any]) {
            do {
                if let source = info[.mediaURL] as? URL {
                    let target = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".mov")
                    try FileManager.default.copyItem(at: source, to: target); parent.selected(target, "video/quicktime")
                } else if let image = info[.originalImage] as? UIImage, let data = image.jpegData(compressionQuality: 0.92) {
                    let target = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".jpg")
                    try data.write(to: target, options: [.atomic, .completeFileProtection]); parent.selected(target, "image/jpeg")
                }
            } catch { parent.dismiss() }
        }
    }
}
