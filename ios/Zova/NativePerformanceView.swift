import SwiftUI

struct NativePerformanceView: View {
    @EnvironmentObject var store: ProductStore
    @State private var days = 7
    @State private var dashboard: JSONValue = .null
    @State private var question = ""
    @State private var answer = ""
    private let metrics = [("Views / impressions", "impressions"), ("Engagements", "engagements"), ("Comments", "comments"), ("Followers", "followers"), ("Posts", "posts")]
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack { Text("Performance").font(.title2.bold()); Spacer(); Button { load() } label: { Image(systemName: "arrow.clockwise").frame(width: 44, height: 44) }.accessibilityLabel("Refresh performance") }
                Picker("Posts published in", selection: $days) { Text("Last 7 days").tag(7); Text("Last 30 days").tag(30) }.pickerStyle(.segmented).onChange(of: days) { _, _ in load() }.disabled(store.busy)
                if store.busy { ProgressView("Reading your accounts…") }
                if !dashboard.isNull {
                    let platforms = dashboard["platforms"].object
                    if !platforms.values.contains(where: { $0["connected"].bool }) {
                        ZovaCard { Text("See what connects with your audience").font(.title3.bold()); Text("Connect an account to see results and decide what to try next."); Button("Connect an account") { store.selectedTab = 3 }.buttonStyle(ZovaPrimary()) }
                    } else {
                        DisclosureGroup("How to read these results") { Text("Available lifetime counters for a sample of posts published in this period—not growth during the period. Followers are current totals. A dash means a metric is unavailable. Compare the same platform and format.").font(.caption).foregroundStyle(.secondary) }
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                            ForEach(metrics, id: \.1) { title, key in
                                if !dashboard["summary"][key].isNull { ZovaCard { Text(title).font(.caption); Text(number(dashboard["summary"][key])).font(.title.bold()) } }
                            }
                        }
                        Text("Platform performance").font(.headline)
                        ForEach(platforms.keys.sorted(), id: \.self) { key in
                            let value = platforms[key] ?? .null
                            if value["connected"].bool {
                                ZovaCard {
                                    HStack { NativePlatformMark(platform: key); Text(value["account"].string).font(.subheadline.bold()) }
                                    HStack { ForEach([("Views", "impressions"), ("Engagements", "engagements"), ("Followers", "followers")], id: \.1) { title, metric in VStack(alignment: .leading) { Text(title).font(.caption2); Text(number(value[metric])).font(.headline) }.frame(maxWidth: .infinity, alignment: .leading) } }
                                    if !value["error"].isNull { Text("Some results are unavailable.").font(.caption).foregroundStyle(.secondary) }
                                }
                            }
                        }
                        if !dashboard["recommendations"].array.isEmpty {
                            Text("What to try").font(.headline)
                            ForEach(Array(dashboard["recommendations"].array.enumerated()), id: \.offset) { _, row in ZovaCard { Text(row["title"].string).font(.subheadline.bold()); Text(row["detail"].string).font(.callout) } }
                        }
                        Text("Top recent posts").font(.headline)
                        ForEach(Array(dashboard["top_posts"].array.enumerated()), id: \.offset) { _, row in
                            ZovaCard {
                                HStack { NativePlatformMark(platform: row["platform"].string); Text(row["text"].string.isEmpty ? "Media post" : row["text"].string).lineLimit(4).font(.callout) }
                                HStack { ForEach(["likes", "comments", "shares", "views"], id: \.self) { key in VStack { Text(key.capitalized).font(.caption2); Text(number(row[key])).font(.caption.bold()) }.frame(maxWidth: .infinity) } }
                                if let url = ProductLinks.external(row["url"].string) { Link("View post ↗", destination: url) }
                            }
                        }
                        NativeField(title: "Ask about your results", text: $question, prompt: "What’s working? What should I create next?", lines: 2)
                        Button("Ask Zova") { Task { await store.perform { let reply = try await store.request("/api/insights", method: "POST", body: .object(["question": .string(question), "days": .integer(days)])); answer = reply["answer"].string } } }.buttonStyle(ZovaPrimary()).disabled(store.busy || question.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                        if !answer.isEmpty { ZovaCard { Text(answer).textSelection(.enabled) } }
                        Text(dashboard["note"].string).font(.caption).foregroundStyle(.secondary)
                    }
                }
            }.padding(18)
        }.refreshable { await update() }.task { await update() }
    }
    private func number(_ value: JSONValue) -> String { value.isNull ? "—" : value.int.formatted() }
    private func load() { Task { await update() } }
    private func update() async { await store.perform { answer = ""; dashboard = try await store.request("/api/analytics/dashboard?days=\(days)") } }
}
