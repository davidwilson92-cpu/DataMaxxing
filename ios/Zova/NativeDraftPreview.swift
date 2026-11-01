import SwiftUI

/// The comparison sheet owns this pool. Each player retains its file for playback.
final class PreviewVideoFile: Sendable {
    let url: URL
    init(_ url: URL) { self.url = url }
    deinit { NativeMediaFiles.remove(url) }
}

@MainActor
final class ComparisonVideoDownloads: ObservableObject {
    private var downloads: [Int: Task<PreviewVideoFile, Error>] = [:]
    private var generation = 0

    func file(for id: Int, download: @escaping @MainActor () async throws -> URL) async throws -> PreviewVideoFile {
        if let existing = downloads[id] { return try await existing.value }
        let current = generation
        let task = Task {
            let file = PreviewVideoFile(try await download())
            try Task.checkCancellation()
            return file
        }
        downloads[id] = task
        do { return try await task.value }
        catch {
            if generation == current { downloads[id] = nil }
            throw error
        }
    }

    func clear() {
        generation += 1
        for task in downloads.values { task.cancel() }
        downloads.removeAll()
    }
}

/// Read-only composition preview. This does not prepare or confirm publication.
struct NativeDraftPreview: View {
    @EnvironmentObject var store: ProductStore
    @StateObject private var videos = ComparisonVideoDownloads()
    var compare = false
    private var platforms: [String] { compare ? SocialPlatform.allCases.map(\.rawValue).filter { !store.draft.variants[$0].isNull } : [store.draft.active] }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                NativeSheetHeader(title: compare ? "Compare versions" : "Preview")
                Text("Final review confirms the exact account, content and settings.").font(.caption).foregroundStyle(.secondary)
                ForEach(platforms, id: \.self) { platform in
                    ZovaCard {
                        HStack { NativePlatformMark(platform: platform); Text(SocialPlatform(rawValue: platform)?.title ?? platform).font(.headline) }
                        Text(note(platform)).font(.caption).foregroundStyle(.secondary)
                        let posts = store.draft.variants[platform]["posts"].strings
                        ForEach(Array(posts.enumerated()), id: \.offset) { index, text in
                            if posts.count > 1 { Text("Post \(index + 1)").font(.caption.bold()) }
                            Text(text).textSelection(.enabled)
                        }
                        ForEach(store.draft.media, id: \.["id"].int) { asset in
                            NativeAssetPreview(asset: asset, comparison: compare ? videos : nil)
                        }
                        if let url = ProductLinks.external(store.draft.workspace["link_url"].string) { Link("Source: " + url.absoluteString, destination: url).font(.caption) }
                    }
                }
            }.padding(20)
        }.preferredColorScheme(.light).onDisappear { videos.clear() }
    }
    private func note(_ platform: String) -> String {
        if platform == "instagram" {
            if store.draft.workspace["instagram_format"].string == "story" { return "Story · only the visual publishes for 24 hours. This text is planning notes; add any text to your file first. Business account required." }
            return store.draft.media.contains(where: { $0["kind"].string == "video" }) ? "Reel · shared to your feed." : "Feed post · a caption for your selected image."
        }
        return ["x": "One post or an ordered thread. Each post must fit the platform limit.", "facebook": "Post text with your selected link or media.", "tiktok": "A caption for your uploaded media. Zova has not generated the video."][platform] ?? ""
    }
}
