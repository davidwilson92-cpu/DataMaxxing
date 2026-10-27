import SwiftUI

struct NativeNextMoveView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    @State var planning = false
    @State private var revision = 0
    @State private var saved = false
    @State private var description = ""
    @State private var direction = ""
    @State private var strategy: JSONValue = .null
    @State private var assumptions: [String] = []
    @State private var proposalInput = ""
    @State private var topic = ""
    @State private var moves: [JSONValue] = []
    @State private var index = 0
    @State private var refinements: [Int: String] = [:]
    @State private var note = ""
    private var current: JSONValue { moves.indices.contains(index) ? moves[index] : .null }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                NativeSheetHeader(title: planning ? "Your strategy" : "✦ Next move")
                if store.busy { ProgressView("Finding the next step…").font(.callout) }
                if planning { strategyForm }
                else if !current.isNull { proposal }
                else {
                    NativeField(title: "What are you posting about?", text: $topic, prompt: "A new launch, a studio moment, something useful…")
                    Button("Find my next post ✦") { run { try await generate() } }.buttonStyle(ZovaPrimary()).disabled(store.busy || topic.trimmingCharacters(in: .whitespacesAndNewlines).count < 3)
                }
                if !note.isEmpty { Text(note).font(.caption).foregroundStyle(.secondary).accessibilityAddTraits(.updatesFrequently) }
                if !planning {
                    Button { planning = true } label: {
                        HStack(spacing: 12) { Image(systemName: "sparkles").font(.title2); VStack(alignment: .leading, spacing: 4) { Text("Your strategy").font(.headline); Text("Give every post a purpose").font(.caption).foregroundStyle(.secondary) }; Spacer(); Image(systemName: "arrow.up.right") }.padding(18).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 17))
                    }.accessibilityIdentifier("your-strategy")
                }
            }.padding(20)
        }.background(.white).preferredColorScheme(.light).foregroundStyle(ZovaDesign.ink).tint(ZovaDesign.purple)
            .task { run { try await load() } }.interactiveDismissDisabled(store.busy)
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
    private var proposal: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 20) {
                HStack { NativePlatformMark(platform: current["platform"].string).colorInvert(); Text(current["format"].string == "story" ? "Story" : "Post").font(.caption); Spacer() }
                Text(current["title"].string).font(.system(size: 25, weight: .bold)).fixedSize(horizontal: false, vertical: true)
                Button {
                    run {
                        try await store.save()
                        let id = current["draft_id"].int
                        let reply = id > 0 ? JSONValue.object(["draft_id": .integer(id)]) : try await store.request("/api/strategy/actions/\(current["id"].int)/draft", method: "POST", body: .object([:]))
                        guard reply["draft_id"].int > 0 else { throw ZovaFailure.invalidResponse }
                        try await store.openDraft(reply["draft_id"].int); dismiss()
                    }
                } label: { HStack { Text(current["draft_id"].int > 0 ? "Open draft" : "Draft post"); Spacer(); Image(systemName: "arrow.right") }.padding(.horizontal, 14) }.buttonStyle(ZovaPrimary()).disabled(store.busy)
            }.padding(20).foregroundStyle(.white).background(ZovaDesign.hero, in: RoundedRectangle(cornerRadius: 21))
            VStack(alignment: .leading, spacing: 9) {
                Text("AI recommendation").font(.subheadline.bold())
                Text(concise(current["reason"].string, words: 32)).font(.callout)
                if !current["basis"].string.isEmpty { Text(current["basis"].string).font(.caption).foregroundStyle(.secondary) }
            }.padding(16).frame(maxWidth: .infinity, alignment: .leading).background(ZovaDesign.pale, in: RoundedRectangle(cornerRadius: 15))
            if !current["source"].isNull {
                DisclosureGroup("Source") {
                    VStack(alignment: .leading, spacing: 8) {
                        if current["stale"].bool { Text("This evidence needs refreshing.") }
                        if let url = ProductLinks.external(current["source"]["url"].string) { Link(current["source"]["title"].string.isEmpty ? "Read source ↗" : current["source"]["title"].string, destination: url) }
                        Text(current["source"]["checked_at"].string).font(.caption).foregroundStyle(.secondary)
                    }.padding(.top, 8)
                }.font(.caption)
            }
            DisclosureGroup("Refine this idea") {
                VStack(spacing: 10) {
                    let id = current["id"].int
                    NativeField(title: "What would you change?", text: Binding(get: { refinements[id] ?? "" }, set: { refinements[id] = String($0.prefix(500)) }), prompt: "More playful, easier to film, a different angle…", lines: 2)
                    Button("Shape this idea") { run { try await generate(refine: true) } }.buttonStyle(ZovaPrimary()).disabled(store.busy || (refinements[id] ?? "").trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }.padding(.top, 12)
            }.font(.subheadline)
            HStack {
                Button { index -= 1; note = "" } label: { Image(systemName: "arrow.left").frame(width: 44, height: 44) }.disabled(index == 0 || store.busy).accessibilityLabel("Previous idea")
                Spacer(); Text("Idea \(index + 1)").font(.caption).foregroundStyle(.secondary); Spacer()
                Button { if index + 1 < moves.count { index += 1; note = "" } else { run { try await generate() } } } label: { Image(systemName: "arrow.right").frame(width: 44, height: 44) }.disabled(store.busy).accessibilityLabel("Next idea")
            }
        }
    }
    private var strategyForm: some View {
        VStack(alignment: .leading, spacing: 18) {
            NativeField(title: "You and your audience", text: $description, prompt: "I run a pottery studio in Leeds for curious beginners. I want more weekend bookings.")
            NativeField(title: "What would you like to post?", text: $direction, prompt: "Studio moments, simple tips, new classes… Two videos a week. Keep it friendly.", lines: 2)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack { ForEach(["Behind the scenes", "Helpful tips", "My latest offer"], id: \.self) { item in Button(item) { direction += (direction.isEmpty ? "" : " · ") + item }.font(.caption).buttonStyle(.bordered) } }
            }
            if proposalInput != description + "\n" + direction || strategy.isNull {
                Button(saved ? "Update my strategy ✦" : "Shape my strategy ✦") { run { try await propose() } }.buttonStyle(ZovaPrimary()).disabled(store.busy || description.trimmingCharacters(in: .whitespacesAndNewlines).count < 3)
            } else {
                Text(saved ? "Saved to your brand" : "Your proposed strategy").font(.subheadline.bold()).foregroundStyle(ZovaDesign.purple)
                ZovaCard {
                    ForEach([("Aim", "goal"), ("Post about", "themes"), ("Pace", "rhythm")], id: \.0) { label, key in
                        if !strategy[key].string.isEmpty { VStack(alignment: .leading, spacing: 5) { Text(label).font(.caption.bold()); Text(concise(strategy[key].string, words: 22)).font(.callout) } }
                    }
                }
                if !assumptions.isEmpty { Text("Check: " + assumptions.prefix(2).map { concise($0, words: 16) }.joined(separator: " ")).font(.caption).foregroundStyle(.secondary) }
                DisclosureGroup("Public search topics") { Text(strategy["themes"].string).font(.callout); Text("Used for public searches. Keep your description non-confidential.").font(.caption) }
                Button(saved ? "Find my next post →" : "Save strategy") {
                    run {
                        if !saved {
                            let reply = try await store.request("/api/strategy/confirm", method: "POST", body: .object(["revision": .integer(revision), "strategy": strategy]))
                            revision = reply["revision"].int; strategy = reply["confirmed"]; saved = true; moves = []; index = 0
                        } else { planning = false; try await generate() }
                    }
                }.buttonStyle(ZovaPrimary()).disabled(store.busy)
            }
        }.disabled(store.busy)
    }
    private func concise(_ text: String, words: Int) -> String {
        let values = text.split(whereSeparator: \.isWhitespace)
        return values.prefix(words).joined(separator: " ") + (values.count > words ? "…" : "")
    }
    private func load() async throws {
        let data = try await store.request("/api/strategy")
        revision = data["revision"].int; saved = !data["confirmed"]["goal"].string.isEmpty
        strategy = data["proposal"]["strategy"].isNull ? (saved ? data["confirmed"] : data["defaults"]) : data["proposal"]["strategy"]
        description = strategy["description"].string.isEmpty ? strategy["goal"].string : strategy["description"].string
        direction = strategy["content_direction"].string.isEmpty ? strategy["themes"].string : strategy["content_direction"].string
        proposalInput = description + "\n" + direction
        if !data["proposal"]["strategy"].isNull { saved = false }
        assumptions = data["proposal"]["assumptions"].strings
        let actions = try await store.request("/api/strategy/actions")
        moves = actions["history"].array + actions["items"].array
        index = actions["history"].array.count
        if !planning && moves.isEmpty && saved { try await generate() }
    }
    private func propose() async throws {
        let reply = try await store.request("/api/strategy/propose", method: "POST", body: .object(["revision": .integer(revision), "brief": .string(description), "content_direction": .string(direction)]))
        revision = reply["revision"].int; strategy = reply["proposal"]["strategy"]
        strategy["description"] = .string(description); strategy["content_direction"] = .string(direction)
        assumptions = reply["proposal"]["assumptions"].strings
        proposalInput = description + "\n" + direction; saved = false; moves = []; index = 0
    }
    private func generate(refine: Bool = false) async throws {
        var body: JSONValue = .object(["revision": .integer(revision), "fresh": .bool(true), "post_only": .bool(true)])
        let context = current["strategy_context"]
        if context["one_off"].bool {
            body["brief"] = context["topic"].string.isEmpty ? context["goal"] : context["topic"]; body["platforms"] = context["platforms"]
        } else if !saved { body["brief"] = .string(topic); body["platforms"] = .strings(store.draft.selected) }
        if refine { body["refine_action_id"] = current["id"]; body["refinement"] = .string(refinements[current["id"].int] ?? "") }
        let reply = try await store.request("/api/strategy/recommend", method: "POST", body: body)
        let items = reply["items"].array
        guard !items.isEmpty else { throw ZovaFailure.server("No new ideas came back. Your existing ideas are kept; try another angle.") }
        let previous = moves.count
        for item in items {
            if let position = moves.firstIndex(where: { $0["id"] == item["id"] }) { moves[position] = item }
            else { moves.append(item) }
        }
        index = previous < moves.count ? previous : max(0, moves.count - items.count)
        if moves.count > 60 { let removed = moves.count - 60; moves.removeFirst(removed); index = max(0, index - removed) }
        note = ""
    }
}
