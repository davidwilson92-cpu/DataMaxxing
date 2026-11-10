import SwiftUI

struct NativeMediaLibrary: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) private var dismiss
    var existing: [Int]
    var limit: Int
    var selected: ([JSONValue]) async throws -> Void
    @State private var rows: [JSONValue] = []
    @State private var picks: [JSONValue] = []
    @State private var query = ""
    @State private var kind = "all"
    @State private var cursor = 0
    @State private var loading = false
    @State private var applying = false
    @State private var error = ""
    @State private var ownerEpoch: Int?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    TextField("Search files", text: $query).textFieldStyle(.roundedBorder).submitLabel(.search).onSubmit { load(reset: true) }.accessibilityLabel("Search saved media").disabled(loading || applying)
                    Picker("Media type", selection: $kind) { Text("All").tag("all"); Text("Photos").tag("image"); Text("Videos").tag("video") }.pickerStyle(.segmented).onChange(of: kind) { _, _ in load(reset: true) }.disabled(loading || applying)
                    if loading { ProgressView("Loading saved media") }
                    if !error.isEmpty { Text(error).foregroundStyle(.secondary); Button("Try again") { load(reset: true) }.frame(minHeight: 44) }
                    if rows.isEmpty && !loading && error.isEmpty { Text("No matching files. Upload from your device to get started.").foregroundStyle(.secondary) }
                    LazyVStack(spacing: 12) { ForEach(rows, id: \.["id"].int) { asset in assetRow(asset) } }
                    if cursor > 0 { Button("Load more") { load(reset: false) }.frame(minHeight: 44).disabled(loading) }
                }.padding(16)
            }
            .safeAreaInset(edge: .bottom) {
                Button("Use selected (\(picks.count))") {
                    guard !applying, ownerEpoch == store.authority else { dismiss(); return }; applying = true
                    Task { do { try await selected(picks); dismiss() } catch { self.error = error.localizedDescription }; applying = false }
                }.buttonStyle(ZovaPrimary()).disabled(picks.isEmpty || applying || loading).padding().background(Color.white)
            }
            .navigationTitle("Saved media").navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() }.disabled(applying) } }
            .interactiveDismissDisabled(applying)
            .background(Color.white).preferredColorScheme(.light).tint(ZovaDesign.purple)
            .task { load(reset: true) }
        }
    }
    private func assetRow(_ asset: JSONValue) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                if picks.contains(where: { $0["id"] == asset["id"] }) { picks.removeAll { $0["id"] == asset["id"] } }
                else if picks.count < limit { picks.append(asset) }
                else { error = "Choose up to \(limit) more files." }
            } label: {
                HStack(spacing: 12) {
                    Image(systemName: existing.contains(asset["id"].int) || picks.contains(where: { $0["id"] == asset["id"] }) ? "checkmark.circle.fill" : "circle")
                    CampaignMediaTile(asset: asset, height: 64).frame(width: 64, height: 64).clipped().allowsHitTesting(false)
                    VStack(alignment: .leading) { Text(asset["filename"].string).font(.callout); Text(asset["states"].strings.joined(separator: " · ").replacingOccurrences(of: "_", with: " ")).font(.caption).foregroundStyle(.secondary) }
                    Spacer(minLength: 0)
                }.frame(minHeight: 64).contentShape(Rectangle())
            }.buttonStyle(.plain).disabled(existing.contains(asset["id"].int) || applying)
            .accessibilityIdentifier("library-asset-\(asset["id"].int)")
            .accessibilityLabel(asset["filename"].string + (existing.contains(asset["id"].int) ? ", already attached" : ""))
            if !asset["uses"].array.isEmpty { DisclosureGroup("Used in \(asset["uses"].array.count) places") {
                ForEach(Array(asset["uses"].array.enumerated()), id: \.offset) { _, use in Text(use["title"].string + " · " + use["state"].string.replacingOccurrences(of: "_", with: " ")).font(.caption).frame(maxWidth: .infinity, alignment: .leading) }
            }.font(.caption) }
        }.padding(12).background(RoundedRectangle(cornerRadius: 12).stroke(ZovaDesign.line))
    }
    private func load(reset: Bool) {
        guard !loading, !applying else { return }
        loading = true; error = ""
        let epoch = store.authority
        if let ownerEpoch, ownerEpoch != epoch { dismiss(); return }; ownerEpoch = epoch
        if reset { rows = []; picks = []; cursor = 0 }
        var components = URLComponents(); components.queryItems = [URLQueryItem(name: "q", value: query), URLQueryItem(name: "kind", value: kind)]
        if cursor > 0 { components.queryItems?.append(URLQueryItem(name: "before", value: String(cursor))) }
        Task {
            defer { loading = false }
            do {
                let result = try await store.request("/api/media/library?" + (components.percentEncodedQuery ?? ""))
                guard epoch == store.authority, !Task.isCancelled else { dismiss(); return }
                rows += result["assets"].array; cursor = result["next_before"].int
            } catch { self.error = error.localizedDescription }
        }
    }
}

struct NativeLearningEvidence: View {
    let value: JSONValue
    private var label: String {
        if isStale { return "Evidence needs refresh" }
        return value["sample_size"].int > 0 ? "Evidence · \(value["sample_size"].int) posts" : "An idea to test"
    }
    private var isStale: Bool {
        guard let date = ProductLinks.date(value["checked_at"].string) else { return false }
        return Date().timeIntervalSince(date) > 86400
    }
    var body: some View {
        if !value.isNull {
            DisclosureGroup(label) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(value["summary"].string)
                    Text(value["note"].string)
                    if !value["checked_at"].string.isEmpty { Text("Evidence checked: " + value["checked_at"].string) }
                    ForEach(Array(value["examples"].array.enumerated()), id: \.offset) { _, post in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(post["text"].string.isEmpty ? "Post without a caption" : post["text"].string)
                            Text(post["platform"].string + " · " + post["created_at"].string).foregroundStyle(.secondary)
                            Text(["likes","comments","shares","views"].map { key in key + ": " + (post["metrics"][key].isNull ? "Unavailable" : String(post["metrics"][key].int)) }.joined(separator: " · "))
                        }.padding(8).background(ZovaDesign.pale)
                    }
                }.padding(.top, 8)
            }.font(.caption).frame(minHeight: 44)
        }
    }
}
