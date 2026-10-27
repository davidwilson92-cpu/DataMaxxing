import SwiftUI
import AVKit
import ImageIO

enum ZovaDesign {
    static let ink = Color(red: 0.08, green: 0.06, blue: 0.12)
    static let purple = Color(red: 0.49, green: 0.23, blue: 0.92)
    static let violet = Color(red: 0.73, green: 0.56, blue: 1)
    static let pale = Color(red: 0.96, green: 0.94, blue: 0.98)
    static let line = Color(red: 0.87, green: 0.84, blue: 0.91)
    static let dark = Color(red: 0.031, green: 0.024, blue: 0.059)
    static let hero = LinearGradient(colors: [ink, Color(red: 0.20, green: 0.10, blue: 0.29)], startPoint: .bottomLeading, endPoint: .topTrailing)
}

struct ZovaPrimary: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label.font(.body.weight(.semibold)).frame(maxWidth: .infinity, minHeight: 48)
            .foregroundStyle(.white).background(ZovaDesign.purple.opacity(configuration.isPressed ? 0.7 : 1), in: RoundedRectangle(cornerRadius: 13))
    }
}
struct ZovaCard<Content: View>: View {
    @ViewBuilder var content: () -> Content
    var body: some View { VStack(alignment: .leading, spacing: 14, content: content).padding(18).frame(maxWidth: .infinity, alignment: .leading).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 18)) }
}
struct NativePlatformMark: View {
    let platform: String
    var size: CGFloat = 24
    var light = false
    var body: some View {
        Group {
            if UIImage(named: "Platform-" + platform) != nil {
                if light && platform != "instagram" { Image("Platform-" + platform).resizable().scaledToFit().colorInvert() }
                else { Image("Platform-" + platform).resizable().scaledToFit() }
            } else {
                Text(["x":"𝕏", "instagram":"◎", "facebook":"f", "tiktok":"♪"][platform] ?? "•").font(.system(size: size, weight: .bold))
            }
        }.frame(width: size, height: size).accessibilityLabel(SocialPlatform(rawValue: platform)?.title ?? platform)
    }
}
struct NativeField: View {
    let title: String
    @Binding var text: String
    var prompt = ""
    var lines = 3
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.subheadline.weight(.semibold))
            TextField(title, text: $text, prompt: Text(prompt), axis: .vertical).lineLimit(lines...max(lines, 8))
                .padding(13).background(.background, in: RoundedRectangle(cornerRadius: 12))
                .overlay(RoundedRectangle(cornerRadius: 12).stroke(ZovaDesign.line, lineWidth: 1))
                .accessibilityIdentifier(title)
        }
    }
}
struct NativeSheetHeader: View {
    let title: String
    @Environment(\.dismiss) var dismiss
    var body: some View {
        HStack { Text(title).font(.title3.bold()); Spacer(); Button { dismiss() } label: { Image(systemName: "xmark").frame(width: 44, height: 44).background(ZovaDesign.pale, in: Circle()) }.accessibilityLabel("Close " + title) }
    }
}

struct NativeAssetPreview: View {
    @EnvironmentObject var store: ProductStore
    let asset: JSONValue
    var compact = false
    @State private var image: UIImage?
    @State private var player: AVPlayer?
    @State private var localURL: URL?
    @State private var failed = false
    var body: some View {
        VStack(spacing: 6) {
            Group {
                if let image { Image(uiImage: image).resizable().scaledToFit() }
                else if let player, !compact { VideoPlayer(player: player) }
                else { Image(systemName: asset["kind"].string == "video" ? "play.rectangle" : "photo").font(.title2).foregroundStyle(ZovaDesign.purple) }
            }.frame(maxWidth: compact ? 72 : .infinity).frame(height: compact ? 58 : 200).clipShape(RoundedRectangle(cornerRadius: 12))
            if !compact { Text(failed ? "Preview unavailable. Your attachment is retained." : asset["filename"].string).font(.caption).foregroundStyle(.secondary) }
        }.task(id: asset["id"].int) { await load() }
            .onChange(of: store.selectedTab) { _, _ in player?.pause() }
            .onReceive(NotificationCenter.default.publisher(for: UIApplication.willResignActiveNotification)) { _ in player?.pause() }
            .onDisappear { player?.pause(); NativeMediaFiles.remove(localURL); localURL = nil; player = nil; image = nil }
    }
    private func load() async {
        guard asset["id"].int > 0, !asset["unavailable"].bool else { failed = true; return }
        if compact && asset["kind"].string == "video" { return }
        do {
            let url = try await store.assetFile(asset)
            guard !Task.isCancelled else { NativeMediaFiles.remove(url); return }
            if asset["kind"].string == "video" {
                localURL = url; player = AVPlayer(url: url)
            } else {
                if let source = CGImageSourceCreateWithURL(url as CFURL, [kCGImageSourceShouldCache: false] as CFDictionary),
                   let thumbnail = CGImageSourceCreateThumbnailAtIndex(source, 0, [
                    kCGImageSourceCreateThumbnailFromImageAlways: true,
                    kCGImageSourceCreateThumbnailWithTransform: true,
                    kCGImageSourceThumbnailMaxPixelSize: compact ? 240 : 1400,
                    kCGImageSourceShouldCacheImmediately: true
                   ] as CFDictionary) { image = UIImage(cgImage: thumbnail) }
                failed = image == nil; NativeMediaFiles.remove(url)
            }
        } catch { failed = true }
    }
}

struct NativeInlineStatus: View {
    let value: JSONValue
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Publication results").font(.headline)
            ForEach(value["results"].object.keys.sorted(), id: \.self) { platform in
                let result = value["results"][platform]
                VStack(alignment: .leading, spacing: 7) {
                    HStack { NativePlatformMark(platform: platform); Text(status(result)).font(.subheadline.bold()) }
                    if !result["error"].string.isEmpty { Text(result["error"].string).font(.callout) }
                    if result["requires_tiktok_completion"].bool { Text("Finish publishing in TikTok. This has not been posted to your feed.").font(.callout) }
                    if let url = ProductLinks.external(result["url"].string) { Link("View post ↗", destination: url) }
                    if !result["support_reference"].string.isEmpty { Text("Support: " + result["support_reference"].string).font(.caption).foregroundStyle(.secondary) }
                }
            }
        }
    }
    private func status(_ result: JSONValue) -> String {
        if result["delivered_to_inbox"].bool { return "Delivered to TikTok inbox" }
        let state = result["status"].string
        if ["unknown", "unconfirmed"].contains(state) { return "Outcome unconfirmed — check the account before retrying" }
        return ["pending":"Processing", "publishing":"Publishing", "published":"Published", "scheduled":"Scheduled", "failed":"Failed", "cancelled":"Cancelled"][state] ?? state.replacingOccurrences(of: "_", with: " ").capitalized
    }
}
