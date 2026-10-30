import SwiftUI
import AVKit
import ImageIO

/// Observe background taps without consuming buttons, scrolling or text input.
struct NativeKeyboardDismiss: UIViewRepresentable {
    final class Host: UIView, UIGestureRecognizerDelegate {
        private weak var installedWindow: UIWindow?
        private lazy var tap = UITapGestureRecognizer(target: self, action: #selector(dismissKeyboard))
        override func didMoveToWindow() {
            super.didMoveToWindow()
            installedWindow?.removeGestureRecognizer(tap)
            installedWindow = window
            tap.cancelsTouchesInView = false; tap.delegate = self
            window?.addGestureRecognizer(tap)
        }
        func detach() { installedWindow?.removeGestureRecognizer(tap) }
        @objc private func dismissKeyboard() { installedWindow?.endEditing(true) }
        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldReceive touch: UITouch) -> Bool {
            var view = touch.view
            while let current = view {
                if current is UITextField || current is UITextView || current is UIControl { return false }
                view = current.superview
            }
            return true
        }
        func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer, shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer) -> Bool { true }
    }
    func makeUIView(context: Context) -> Host { Host() }
    func updateUIView(_ uiView: Host, context: Context) { }
    static func dismantleUIView(_ uiView: Host, coordinator: ()) { uiView.detach() }
}

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
        configuration.label.font(.body.weight(.semibold)).multilineTextAlignment(.center)
            .fixedSize(horizontal: false, vertical: true).padding(.vertical, 10).frame(maxWidth: .infinity, minHeight: 48)
            .foregroundStyle(.white).background(ZovaDesign.purple.opacity(configuration.isPressed ? 0.7 : 1), in: RoundedRectangle(cornerRadius: 13))
    }
}
struct ZovaCard<Content: View>: View {
    @ViewBuilder var content: () -> Content
    var body: some View { VStack(alignment: .leading, spacing: 14, content: content).padding(18).frame(maxWidth: .infinity, alignment: .leading).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 18)) }
}

/// Text rows reflow at accessibility sizes without shrinking the user's text.
struct NativeAdaptiveRow<Content: View>: View {
    @Environment(\.dynamicTypeSize) private var textSize
    var spacing: CGFloat = 12
    @ViewBuilder var content: () -> Content
    var body: some View {
        let layout = textSize.isAccessibilitySize
            ? AnyLayout(VStackLayout(alignment: .leading, spacing: spacing))
            : AnyLayout(HStackLayout(spacing: spacing))
        layout { content() }.frame(maxWidth: .infinity, alignment: .leading)
    }
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
                .multilineTextAlignment(.leading)
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

struct NativePasswordField: View {
    let title: String
    @Binding var text: String
    var newPassword = false
    @State private var visible = false
    var body: some View {
        HStack {
            Group {
                if visible { TextField(title, text: $text) }
                else { SecureField(title, text: $text) }
            }.textContentType(newPassword ? .newPassword : .password).textInputAutocapitalization(.never).autocorrectionDisabled()
            Button { visible.toggle() } label: { Image(systemName: visible ? "eye.slash" : "eye").frame(width: 44, height: 44) }
                .accessibilityLabel((visible ? "Hide " : "Show ") + title.lowercased())
        }.padding(.leading, 12).background(.white.opacity(0.06), in: RoundedRectangle(cornerRadius: 10))
    }
}

struct NativeTimezonePicker: View {
    @Binding var selection: String
    @State private var search = ""
    var body: some View {
        NavigationStack {
            List(TimeZone.knownTimeZoneIdentifiers.filter { search.isEmpty || $0.replacingOccurrences(of: "_", with: " ").localizedCaseInsensitiveContains(search) }, id: \.self) { value in
                Button { selection = value } label: { HStack { Text(value.replacingOccurrences(of: "_", with: " ")); Spacer(); if selection == value { Image(systemName: "checkmark") } } }
            }.searchable(text: $search).navigationTitle("Timezone")
                .safeAreaInset(edge: .top) { Button("Use this iPhone’s timezone") { selection = TimeZone.current.identifier }.padding() }
                .toolbar { ToolbarItem(placement: .confirmationAction) { NativeTimezoneDone() } }
        }.preferredColorScheme(.light).tint(ZovaDesign.purple)
    }
}
private struct NativeTimezoneDone: View {
    @Environment(\.dismiss) var dismiss
    var body: some View { Button("Done") { dismiss() } }
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
