import SwiftUI

struct NativeRecoveryComparison: View {
    @EnvironmentObject var store: ProductStore
    let saved: ProductDraft
    let useSaved: () -> Void
    @State private var discard = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                NativeSheetHeader(title: "Compare changes")
                version("On this iPhone", ProductDraft(store.recovery))
                version("Saved to your account", saved)
                Text("Keep editing the local copy, save it as a new draft, or use the saved version. Nothing is overwritten automatically.").font(.callout)
                Button("Use saved version") { discard = true }.buttonStyle(.bordered)
            }.padding(20)
        }.preferredColorScheme(.light)
            .confirmationDialog("Discard local edits and use the current saved version?", isPresented: $discard, titleVisibility: .visible) {
                Button("Discard local edits", role: .destructive, action: useSaved)
            }
    }
    private func version(_ title: String, _ draft: ProductDraft) -> some View {
        ZovaCard {
            Text(title).font(.headline)
            if !draft.composer.isEmpty { Text(draft.composer).textSelection(.enabled) }
            ForEach(SocialPlatform.allCases) { platform in
                ForEach(Array(draft.variants[platform.rawValue]["posts"].strings.enumerated()), id: \.offset) { _, caption in
                    HStack(alignment: .top) { NativePlatformMark(platform: platform.rawValue); Text(caption).textSelection(.enabled) }
                }
            }
            if draft.composer.isEmpty && draft.variants.object.isEmpty { Text(draft.brief).textSelection(.enabled) }
            Text("\(draft.media.count) attachments · Revision \(draft.revision)").font(.caption).foregroundStyle(.secondary)
        }
    }
}
