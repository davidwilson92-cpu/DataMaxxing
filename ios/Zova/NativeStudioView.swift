import SwiftUI
import PhotosUI
import UniformTypeIdentifiers
import AVFoundation

struct PickedMedia: Transferable {
    let url: URL
    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(importedContentType: .movie) { received in
            let target = try NativeMediaFiles.copyOwned(received.file, extension: received.file.pathExtension.isEmpty ? "mov" : received.file.pathExtension)
            return PickedMedia(url: target)
        }
        FileRepresentation(importedContentType: .image) { received in
            let target = try NativeMediaFiles.copyOwned(received.file, extension: received.file.pathExtension.isEmpty ? "jpg" : received.file.pathExtension)
            return PickedMedia(url: target)
        }
    }
}

struct NativeStudioView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dynamicTypeSize) private var textSize
    @Environment(\.verticalSizeClass) private var verticalSize
    @Binding var nextMove: Bool
    @Binding var strategy: Bool
    @FocusState private var focused: Bool
    @State private var history = false
    @State private var options = false
    @State private var importer = false
    @State private var camera = false
    @State private var picker: [PhotosPickerItem] = []
    @State private var recoveryExport: URL?
    @State private var compared: ProductDraft?
    @FocusState private var captionEditing: Bool
    @State private var discardRecovery = false
    @State private var previewMode: String?
    private var scrollingComposer: Bool { textSize.isAccessibilitySize || verticalSize == .compact }
    var body: some View {
        VStack(spacing: 0) {
            if verticalSize != .compact || (!focused && !captionEditing) { header }
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(alignment: .leading, spacing: 22) {
                        if !store.recovery.isNull {
                            ZovaCard {
                                Text("Recover unsaved changes").font(.headline)
                                Text("There’s a copy saved on this iPhone.").font(.callout)
                                Button("Resume editing") { run { try await store.restoreRecovery() } }
                                Button("Save as new draft") { run { try await store.restoreRecovery(asNew: true) } }
                                Button("Compare saved version") { run { compared = try await store.savedVersion() } }
                                Button("Save a copy to Files") { exportRecovery() }
                                Button("Discard local copy", role: .destructive) { discardRecovery = true }
                            }
                        }
                        if store.saveStatus.hasPrefix("Not saved") {
                            Button("Retry save") { run { try await store.save() } }
                        }
                        ForEach(Array(store.draft.conversation.enumerated()), id: \.offset) { _, message in
                            HStack {
                                if message["role"].string == "user" { Spacer(minLength: 24) }
                                VStack(alignment: .leading, spacing: 10) {
                                    Text(message["content"].string).textSelection(.enabled)
                                    let media = message["media"].array.isEmpty ? store.draft.media.filter { message["media_asset_ids"].array.contains($0["id"]) } : message["media"].array
                                    ForEach(media, id: \.["id"].int) { asset in
                                        NativeAssetPreview(asset: asset)
                                        if store.draft.mediaIDs.array.contains(asset["id"]) && store.draft.editable {
                                            Button("Remove from post") { store.removeMedia(asset["id"].int) }.font(.caption).disabled(store.busy)
                                        } else { Text(store.draft.mediaIDs.array.contains(asset["id"]) ? "Attached to post" : "Not in current post").font(.caption).foregroundStyle(.secondary) }
                                    }
                                }.padding(16).background(message["role"].string == "user" ? ZovaDesign.pale : .clear, in: RoundedRectangle(cornerRadius: 20))
                                if message["role"].string != "user" { Spacer(minLength: 24) }
                            }
                        }
                        if !store.draft.variants.object.isEmpty { caption }
                        if !store.mediaNotice.isEmpty { Text(store.mediaNotice).font(.caption).foregroundStyle(.secondary) }
                        if !store.draft.workspace["pending_message"].string.isEmpty && !store.busy {
                            Button("Retry this idea") { run { try await store.send(retry: true) } }.buttonStyle(.bordered)
                        }
                        if !store.results.isNull {
                            ZovaCard { NativeInlineStatus(value: store.results); Button("Refresh results") { run { try await store.refreshResults() } } }
                        }
                        if store.busy && !store.backgroundSaving { HStack { ProgressView(); Text("Working…").font(.callout).foregroundStyle(.secondary) }.accessibilityIdentifier("studio-working") }
                        if scrollingComposer && store.draft.editable && !captionEditing { composer.id("composer") }
                        Color.clear.frame(height: 1).id("bottom")
                    }.padding(.horizontal, 18).padding(.vertical, 16)
                }.scrollDismissesKeyboard(.interactively)
                    .onChange(of: store.draft.conversation.count) { _, _ in withAnimation { proxy.scrollTo("bottom", anchor: .bottom) } }
                    .onChange(of: store.busy) { _, _ in if !focused && !captionEditing { withAnimation { proxy.scrollTo("bottom", anchor: .bottom) } } }
                    .onChange(of: focused) { _, editing in if editing && scrollingComposer { proxy.scrollTo("composer", anchor: .bottom) } }
            }
            if store.draft.editable {
                if captionEditing {
                    HStack { Text("Editing caption").font(.caption).foregroundStyle(.secondary); Spacer(); Button("Done") { captionEditing = false }.accessibilityIdentifier("finish-editing") }
                        .padding(.horizontal, 18).frame(minHeight: 44).background(Color.white)
                } else if !scrollingComposer { composer }
            } else { Button("+ New post") { run { try await store.newPost() } }.buttonStyle(ZovaPrimary()).padding(18) }
        }.foregroundStyle(ZovaDesign.ink)
            .confirmationDialog("Discard the unsaved copy on this iPhone? Your server draft stays unchanged.", isPresented: $discardRecovery, titleVisibility: .visible) { Button("Discard local copy", role: .destructive) { store.discardRecovery() } }
            .sheet(isPresented: $history) { NativeHistoryView().environmentObject(store) }
            .sheet(isPresented: $options) { NativePostOptionsView().environmentObject(store) }
            .sheet(isPresented: Binding(get: { previewMode != nil }, set: { if !$0 { previewMode = nil } })) {
                NativeDraftPreview(compare: previewMode == "compare").environmentObject(store)
            }
            .sheet(isPresented: Binding(get: { recoveryExport != nil }, set: { if !$0 { clearRecoveryExport() } }), onDismiss: clearRecoveryExport) {
                if let recoveryExport { NativeShare(items: [recoveryExport]) }
            }
            .sheet(isPresented: Binding(get: { compared != nil }, set: { if !$0 { compared = nil } })) {
                if let compared { NativeRecoveryComparison(saved: compared) { run { store.useSavedVersion(try await store.savedVersion()); self.compared = nil } }.environmentObject(store) }
            }
            .fileImporter(isPresented: $importer, allowedContentTypes: [.image, .movie], allowsMultipleSelection: true) { result in
                switch result {
                case .success(let urls):
                    run {
                        try store.validateAttachments(urls.map { UTType(filenameExtension: $0.pathExtension)?.preferredMIMEType ?? "application/octet-stream" })
                        for url in urls {
                            guard url.startAccessingSecurityScopedResource() else { throw ZovaFailure.server("Choose that file again to allow access.") }
                            defer { url.stopAccessingSecurityScopedResource() }
                            try await store.upload(url, name: url.lastPathComponent, mime: UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream")
                        }
                    }
                case .failure(let error): store.handle(error)
                }
            }
            .sheet(isPresented: $camera) { NativeCamera(selected: { url, mime in camera = false; run { defer { NativeMediaFiles.remove(url) }; try await store.upload(url, name: url.lastPathComponent, mime: mime) } }, failed: { error in camera = false; store.handle(error) }) }
            .onChange(of: captionEditing) { _, editing in if editing { store.draft.addHistory() } }
            .onChange(of: picker) { _, items in
                guard !items.isEmpty else { return }
                run {
                    defer { picker = [] }
                    try store.validateAttachments(items.map { $0.supportedContentTypes.contains(where: { $0.conforms(to: .movie) }) ? "video/mp4" : "image/jpeg" })
                    for item in items {
                        guard let media = try await item.loadTransferable(type: PickedMedia.self) else { throw ZovaFailure.server("This photo or video could not be opened.") }
                        defer { NativeMediaFiles.remove(media.url) }
                        try await store.upload(media.url, name: media.url.lastPathComponent, mime: UTType(filenameExtension: media.url.pathExtension)?.preferredMIMEType ?? "application/octet-stream")
                    }
                }
            }
            .onDisappear { clearRecoveryExport() }
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
    private func exportRecovery() {
        do {
            let file = try NativeMediaFiles.create(extension: "json")
            try (store.recovery.isNull ? store.draft.payload : store.recovery).encoded().write(to: file, options: [.atomic, .completeFileProtection])
            recoveryExport = file
        } catch { store.handle(error) }
    }
    private func clearRecoveryExport() { NativeMediaFiles.remove(recoveryExport); recoveryExport = nil }
    private var header: some View {
        VStack(spacing: 5) {
            ViewThatFits(in: .horizontal) {
                HStack(spacing: 10) { brandMark; Spacer(minLength: 0); headerActions }.fixedSize(horizontal: true, vertical: false)
                VStack(alignment: .leading, spacing: 4) { brandMark; headerActions }
            }
            HStack {
                Menu {
                    ForEach(store.account["brand"]["choices"].array, id: \.["id"].int) { brand in
                        Button(brand["name"].string) { run { try await store.switchBrand(brand["id"].int) } }
                    }
                } label: { HStack(spacing: 5) { Text(store.account["brand"]["name"].string); Image(systemName: "chevron.down").font(.caption2) }.font(.caption).foregroundStyle(.secondary).frame(minWidth: 44, minHeight: 44).contentShape(Rectangle()) }.disabled(store.busy).accessibilityIdentifier("brand-selector")
                Spacer()
                Button { history = true } label: { Image(systemName: "clock.arrow.circlepath").frame(width: 44, height: 44).contentShape(Rectangle()) }.accessibilityLabel("Your posts").disabled(store.busy)
            }
        }.padding(.horizontal, 18).padding(.top, 8).padding(.bottom, 4)
    }
    private var brandMark: some View {
        HStack(spacing: 5) { Image("ZovaMark").resizable().scaledToFit().frame(width: 24, height: 26); Text("Zova").font(.title3.bold()) }
    }
    private var headerActions: some View {
        NativeAdaptiveRow(spacing: 10) {
            Button { focused = false; captionEditing = false; run { try await store.newPost() } } label: {
                Label("New post", systemImage: "plus").font(.caption.weight(.medium)).frame(minHeight: 44).contentShape(Rectangle())
            }.disabled(store.busy).accessibilityIdentifier("new-post")
            Button { focused = false; captionEditing = false; nextMove = true } label: {
                Label("Next move", systemImage: "sparkles").font(.subheadline.bold()).padding(.horizontal, 13).padding(.vertical, 8).frame(minHeight: 44).foregroundStyle(.white).background(ZovaDesign.hero, in: Capsule())
            }.accessibilityIdentifier("next-move").disabled(store.busy)
        }
    }
    private var caption: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                ScrollView(.horizontal, showsIndicators: false) { HStack(spacing: 4) {
                ForEach(SocialPlatform.allCases.filter { store.draft.variants.object[$0.rawValue] != nil }) { platform in
                    Button { store.draft.active = platform.rawValue; store.changed() } label: {
                        NativePlatformMark(platform: platform.rawValue).frame(width: 44, height: 44).background(store.draft.active == platform.rawValue ? ZovaDesign.pale : .clear, in: RoundedRectangle(cornerRadius: 12))
                    }.accessibilityLabel("Edit " + platform.title + " caption")
                }
                } }.frame(maxWidth: .infinity, alignment: .leading)
                Button { UIPasteboard.general.string = store.draft.variants[store.draft.active]["posts"].strings.joined(separator: "\n\n") } label: { Image(systemName: "doc.on.doc").frame(width: 44, height: 44) }.accessibilityLabel("Copy caption")
                if !store.draft.workspace["text_history"].array.isEmpty {
                    Button { store.draft.undo(); store.changed() } label: { Image(systemName: "arrow.uturn.backward").frame(width: 44, height: 44) }.accessibilityLabel("Undo caption change")
                }
                Menu {
                    Button("Preview") { captionEditing = false; previewMode = "preview" }
                    if store.draft.variants.object.count > 1 { Button("Compare versions") { captionEditing = false; previewMode = "compare" } }
                    if store.draft.editable {
                        ForEach(SocialPlatform.allCases.filter { store.draft.variants[$0.rawValue].isNull }) { platform in
                            Button("Add " + platform.title) {
                                store.draft.composer = "Add a \(platform.title) version of this post"; store.changed(); captionEditing = false; focused = true
                            }
                        }
                    }
                } label: { Image(systemName: "ellipsis").frame(width: 44, height: 44) }.accessibilityLabel("More caption options").disabled(store.busy)
            }
            ForEach(Array(store.draft.variants[store.draft.active]["posts"].strings.enumerated()), id: \.offset) { index, _ in
                TextField("Edit caption", text: Binding(get: { store.caption(store.draft.active, index: index) }, set: { store.editCaption(store.draft.active, index: index, text: $0) }), axis: .vertical)
                    .lineLimit(4...20).padding(16).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 16))
                    .focused($captionEditing).disabled((store.busy && !store.backgroundSaving) || !store.draft.editable).accessibilityIdentifier("caption-\(index)")
                if store.draft.active == "x" {
                    Text("\(store.caption("x", index: index).count) / 280").font(.caption).foregroundStyle(.secondary)
                }
            }
            if store.draft.editable {
                NativeAdaptiveRow {
                    Button("Schedule") { focused = false; captionEditing = false; store.reviewMode = "schedule"; store.showReview = true }.buttonStyle(.bordered)
                    Button("Review post →") { focused = false; captionEditing = false; store.reviewMode = "publish"; store.showReview = true }.buttonStyle(ZovaPrimary()).accessibilityIdentifier("review-draft")
                }.disabled(store.busy)
            }
        }
    }
    private var unsentMedia: [JSONValue] {
        store.draft.unsentMedia
    }
    private var composer: some View {
        VStack(spacing: 6) {
            VStack(alignment: .leading, spacing: 10) {
                if !unsentMedia.isEmpty {
                    ScrollView(.horizontal) { HStack { ForEach(unsentMedia, id: \.["id"].int) { asset in
                        HStack { NativeAssetPreview(asset: asset, compact: true); Button { store.removeMedia(asset["id"].int) } label: { Image(systemName: "xmark.circle.fill").frame(width: 44, height: 44).contentShape(Rectangle()) }.accessibilityLabel("Remove " + asset["filename"].string) }.padding(5).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 12))
                    } } }
                }
                TextField("Describe your post. Zova drafts the caption…", text: Binding(get: { store.draft.composer }, set: { store.draft.composer = String($0.prefix(12000)); store.changed() }), axis: .vertical)
                    .lineLimit(1...5).focused($focused).accessibilityIdentifier("post-composer").disabled(store.busy && !store.backgroundSaving)
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
                if store.draft.selected.contains("instagram") || store.draft.selected.contains("x") {
                    NativeAdaptiveRow(spacing: 10) {
                        if store.draft.selected.contains("x") {
                            Picker("X format", selection: Binding(get: { store.draft.threadLength }, set: { store.draft.threadLength = $0; store.changed() })) {
                                Text("One post").tag(1); Text("Thread · 3 posts").tag(3); Text("Thread · 5 posts").tag(5)
                            }.pickerStyle(.menu).font(.caption).frame(minWidth: 44, minHeight: 44).accessibilityIdentifier("x-format")
                        }
                        if store.draft.selected.contains("instagram") {
                            Picker("Instagram format", selection: Binding(get: { store.draft.workspace["instagram_format"].string.isEmpty ? "post" : store.draft.workspace["instagram_format"].string }, set: { store.draft.workspace["instagram_format"] = .string($0); store.draft.workspace["instagram_audio"] = .null; store.changed() })) {
                                Text("Post").tag("post"); Text("Story").tag("story")
                            }.pickerStyle(.segmented).accessibilityIdentifier("instagram-format")
                        }
                    }.frame(minHeight: 44).disabled(store.busy && !store.backgroundSaving)
                }
                if store.draft.selected.contains("x") {
                    Text(store.draft.threadLength == 1 ? "One update, up to 280 characters." : "\(store.draft.threadLength) connected posts, read in order.")
                        .font(.caption).foregroundStyle(.secondary).accessibilityIdentifier("x-format-hint")
                }
                HStack {
                    Menu {
                        PhotosPicker(selection: $picker, maxSelectionCount: max(1, 10 - store.draft.media.count), selectionBehavior: .ordered, matching: .any(of: [.images, .videos]), preferredItemEncoding: .compatible) { Label("Photo library", systemImage: "photo") }
                        Button("Choose file", systemImage: "folder") { importer = true }
                        if UIImagePickerController.isSourceTypeAvailable(.camera) { Button("Camera", systemImage: "camera") { openCamera() } }
                    } label: { Image(systemName: "plus").font(.title3).frame(width: 44, height: 44) }.accessibilityLabel("Add attachment").disabled(store.busy)
                    Button("Post options") { focused = false; captionEditing = false; options = true }.font(.subheadline).frame(minHeight: 44).disabled(store.busy)
                    Spacer()
                    Button { focused = false; run { try await store.send() } } label: { Image(systemName: "arrow.up").font(.title2.bold()).foregroundStyle(.white).frame(width: 48, height: 48).background(ZovaDesign.purple.opacity(store.draft.composer.isEmpty ? 0.4 : 1), in: Circle()) }.accessibilityLabel("Send idea").disabled(store.busy || store.draft.composer.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }.padding(14).background(Color.white, in: RoundedRectangle(cornerRadius: 22)).overlay(RoundedRectangle(cornerRadius: 22).stroke(focused ? ZovaDesign.purple : ZovaDesign.line)).padding(.horizontal, 14)
            if !focused { NativeAdaptiveRow(spacing: 6) { Text(store.saveStatus); Text("Nothing posts without your approval.") }.font(.caption2).foregroundStyle(.secondary).padding(.horizontal, 18) }
        }.padding(.bottom, 8)
    }
    private func openCamera() {
        Task {
            let status = AVCaptureDevice.authorizationStatus(for: .video)
            var allowed = status == .authorized
            if status == .notDetermined { allowed = await AVCaptureDevice.requestAccess(for: .video) }
            if allowed { camera = true }
            else { store.handle(ZovaFailure.server("Allow camera access for Zova in iPhone Settings, or choose an existing photo or video.")) }
        }
    }
}

struct NativeHistoryView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    @State private var query = ""
    var body: some View {
        NavigationStack {
            List {
                ForEach(store.drafts, id: \.["id"].int) { row in
                    Button { Task { await store.perform { try await store.openDraft(row["id"].int); dismiss() } } } label: {
                        VStack(alignment: .leading, spacing: 6) { Text(row["title"].string).foregroundStyle(.primary); Text(row["status"].string.capitalized).font(.caption).foregroundStyle(.secondary) }
                    }
                }
                if store.moreDrafts { Button("Load older posts") { Task { await store.perform { try await store.loadDrafts(search: query, more: true) } } }.disabled(store.busy) }
            }.navigationTitle("Your posts").searchable(text: $query)
                .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Close") { dismiss() } } }
                .task { await load() }.onSubmit(of: .search) { Task { await load() } }
        }
    }
    private func load() async { await store.perform { try await store.loadDrafts(search: query) } }
}

struct NativeCamera: UIViewControllerRepresentable {
    let selected: (URL, String) -> Void
    let failed: (Error) -> Void
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
                    let target = try NativeMediaFiles.copyOwned(source, extension: "mov")
                    parent.selected(target, "video/quicktime")
                } else if let image = info[.originalImage] as? UIImage, let data = image.jpegData(compressionQuality: 0.92) {
                    let target = try NativeMediaFiles.create(extension: "jpg")
                    try data.write(to: target, options: [.atomic, .completeFileProtection]); parent.selected(target, "image/jpeg")
                } else { throw ZovaFailure.server("The camera could not save that attachment. Please try again.") }
            } catch { parent.failed(error); parent.dismiss() }
        }
    }
}
