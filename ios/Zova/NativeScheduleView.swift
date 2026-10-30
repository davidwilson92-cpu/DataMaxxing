import SwiftUI

struct NativeDraftRow: View {
    @EnvironmentObject var store: ProductStore
    let row: JSONValue
    var open: (() async throws -> Void)? = nil
    let changed: () async throws -> Void
    @State private var rename = false
    @State private var title = ""
    @State private var delete = false
    var body: some View {
        ZovaCard {
            HStack(alignment: .top) {
                if !row["thumbnail"].isNull { NativeAssetPreview(asset: row["thumbnail"], compact: true) }
                Button { run { if let open { try await open() } else { try await store.openDraft(row["id"].int) } } } label: { VStack(alignment: .leading, spacing: 7) { Text(row["title"].string).font(.headline).foregroundStyle(.primary).lineLimit(2); Text(row["status"].string.capitalized).font(.caption).foregroundStyle(.secondary) } }.buttonStyle(.plain)
                Spacer()
                Menu { Button("Rename") { title = row["title"].string; rename = true }; if ["draft", "failed", "cancelled"].contains(row["status"].string) { Button("Delete", role: .destructive) { delete = true } } } label: { Image(systemName: "ellipsis").frame(width: 44, height: 44) }.accessibilityLabel("Post options")
            }
            HStack { ForEach(row["platforms"].strings, id: \.self) { NativePlatformMark(platform: $0, size: 20) } }
            ForEach(Array(row["links"].array.enumerated()), id: \.offset) { _, link in if let url = ProductLinks.external(link["url"].string) { Link("View on " + (SocialPlatform(rawValue: link["platform"].string)?.title ?? "social") + " ↗", destination: url).font(.caption) } }
        }.alert("Rename post", isPresented: $rename) {
            TextField("Title", text: $title)
            Button("Save") { run { _ = try await store.api.form("/drafts/\(row["id"].int)/title", fields: ["title": title, "revision": String(row["revision"].int)], brand: store.brand); try await changed() } }
            Button("Cancel", role: .cancel) { }
        }.confirmationDialog("Delete this unsubmitted draft?", isPresented: $delete) { Button("Delete draft", role: .destructive) { run { _ = try await store.request("/api/drafts/\(row["id"].int)", method: "DELETE"); try await changed() } } }
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
}

struct NativeScheduleEdit: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    let row: JSONValue
    let changed: () async throws -> Void
    @State private var date = Date()
    @State private var confirmCancel = false
    @State private var confirmEdit = false
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            NativeSheetHeader(title: "Scheduled post")
            Text(row["title"].string).font(.title2.bold()); Text(row["excerpt"].string)
            HStack { NativePlatformMark(platform: row["platform"].string); Text(row["account_name"].string) }
            if row["status"].string == "scheduled" {
                DatePicker("Posting time", selection: $date, in: Date()...).environment(\.timeZone, TimeZone(identifier: store.timezone) ?? .current)
                Text(store.timezone).font(.caption)
                Button("Save new time") { run { _ = try await store.request("/api/schedules/\(row["id"].int)/reschedule", method: "POST", body: .object(["scheduled_local": .string(ISO8601DateFormatter().string(from: date)), "expected_updated_at": row["updated_at"]])); try await changed(); dismiss() } }.buttonStyle(ZovaPrimary())
                Button("Edit caption / media") { confirmEdit = true }
                Button("Cancel scheduled post", role: .destructive) { confirmCancel = true }
            } else { Button("Open post and results") { run { try await store.openDraft(row["draft_id"].int); dismiss() } }.buttonStyle(ZovaPrimary()) }
        }.padding(22).disabled(store.busy) }.preferredColorScheme(.light).onAppear { date = ProductLinks.date(row["scheduled_at"].string) ?? Date().addingTimeInterval(3600) }
            .confirmationDialog("Stop all unsent deliveries for this post and edit it? You will need to review and schedule it again.", isPresented: $confirmEdit) {
                Button("Stop deliveries and edit") { run { _ = try await store.request("/api/schedules/drafts/\(row["draft_id"].int)/edit", method: "POST", body: .object(["revision": row["draft_revision"]])); try await store.openDraft(row["draft_id"].int); dismiss() } }
            }.confirmationDialog("Cancel this scheduled delivery?", isPresented: $confirmCancel) { Button("Cancel delivery", role: .destructive) { run { _ = try await store.request("/api/schedules/\(row["id"].int)/cancel", method: "POST", body: .object(["expected_updated_at": row["updated_at"]])); try await changed(); dismiss() } } }
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
}

struct NativeSeriesView: View {
    @EnvironmentObject var store: ProductStore
    @Environment(\.dismiss) var dismiss
    @State private var building = false
    @State private var start = Date().addingTimeInterval(86400)
    @State private var frequency = "weekly"
    @State private var mode = "fresh"
    @State private var count = 4
    @State private var weekdays: Set<Int> = []
    @State private var preview: JSONValue = .null
    @State private var previewSpec: JSONValue = .null
    @State private var requestKey = UUID().uuidString
    @State private var repeatReview: JSONValue = .null
    @State private var repeatID = 0
    @State private var occurrence: JSONValue = .null
    @State private var occurrenceRevision = 0
    @State private var movedDate = Date()
    @State private var future = false
    @State private var occurrenceTimezone = ""
    @State private var resultNote = ""
    var body: some View {
        ScrollView { VStack(alignment: .leading, spacing: 20) {
            NativeSheetHeader(title: "Recurring posts")
            if store.busy { ProgressView() }
            if !resultNote.isEmpty { Text(resultNote).font(.callout) }
            if building { builder }
            else { Button("Plan a series from this draft") { building = true; preview = .null }.buttonStyle(ZovaPrimary()).disabled(store.draft.id == nil || store.draft.brief.isEmpty) }
            if store.draft.id == nil { Text("Open a draft in Studio first to use it as a series template.").font(.caption).foregroundStyle(.secondary) }
            if !repeatReview.isNull {
                Text("Review repeat schedule").font(.headline)
                Text(repeatReview["note"].string).font(.callout)
                ForEach(Array(repeatReview["occurrences"].array.enumerated()), id: \.offset) { _, review in NativeReviewSnapshot(snapshot: review["snapshot"]) }
                Button("Confirm these schedules") { run {
                    let token = repeatReview["token"]; repeatReview = .null
                    let reply = try await store.request("/api/series/\(repeatID)/confirm", method: "POST", body: .object(["token": token]))
                    resultNote = reply["results"].array.map { "Post \($0["draft_id"].int): " + $0["status"].string + ($0["error"].string.isEmpty ? "" : " — " + $0["error"].string) }.joined(separator: "\n")
                    try await reload()
                } }.buttonStyle(ZovaPrimary()).disabled(store.busy)
            }
            ForEach(store.series, id: \.["id"].int) { series in seriesCard(series) }
        }.padding(20) }.preferredColorScheme(.light).task { run { try await reload() } }.interactiveDismissDisabled(store.busy)
            .sheet(isPresented: Binding(get: { !occurrence.isNull }, set: { if !$0 { occurrence = .null } })) {
                VStack(alignment: .leading, spacing: 20) {
                    NativeSheetHeader(title: "Move occurrence")
                    DatePicker("New time", selection: $movedDate, in: Date()...).environment(\.timeZone, TimeZone(identifier: occurrenceTimezone) ?? .current)
                    Text(occurrenceTimezone).font(.caption)
                    Toggle("This and future occurrences", isOn: $future)
                    Text("Changed posts need a fresh review before scheduling.").font(.caption)
                    Button("Save new time") { run {
                        _ = try await store.request("/api/series/occurrences/\(occurrence["id"].int)/time", method: "POST", body: .object(["revision": .integer(occurrenceRevision), "local_time": .string(ISO8601DateFormatter().string(from: movedDate)), "scope": .string(future ? "future" : "one")]))
                        occurrence = .null; try await reload()
                    } }.buttonStyle(ZovaPrimary())
                    Spacer()
                }.padding(22).presentationDetents([.medium])
            }
    }
    private var builder: some View {
        VStack(alignment: .leading, spacing: 16) {
            Picker("Content", selection: $mode) { Text("Fresh drafts").tag("fresh"); Text("Repeat this draft").tag("repeat") }.pickerStyle(.segmented)
            DatePicker("First date", selection: $start, in: Date()...).environment(\.timeZone, TimeZone(identifier: store.timezone) ?? .current)
            Text(store.timezone).font(.caption)
            Picker("Frequency", selection: $frequency) { Text("Weekly").tag("weekly"); Text("Daily").tag("daily") }.pickerStyle(.segmented)
            if frequency == "weekly" {
                HStack { ForEach(Array(["M", "T", "W", "T", "F", "S", "S"].enumerated()), id: \.offset) { day, label in Button(label) { if weekdays.contains(day) { weekdays.remove(day) } else { weekdays.insert(day) } }.frame(maxWidth: .infinity, minHeight: 44).background(weekdays.contains(day) ? ZovaDesign.pale : .clear, in: RoundedRectangle(cornerRadius: 8)) } }
            }
            Stepper("\(count) occurrences", value: $count, in: 1...26)
            Button("Preview dates") { run { try await store.save(); previewSpec = specification(); preview = try await store.request("/api/series/preview", method: "POST", body: previewSpec) } }.buttonStyle(.bordered)
            if !preview.isNull {
                Text(preview["note"].string).font(.caption)
                ForEach(Array(preview["times"].array.enumerated()), id: \.offset) { _, item in Text(item["local"].string).font(.callout) }
                Button("Create draft series") { run {
                    guard previewSpec == specification() else { throw ZovaFailure.server("Settings changed. Preview the dates again.") }
                    _ = try await store.request("/api/series", method: "POST", body: previewSpec)
                    requestKey = UUID().uuidString; building = false; preview = .null; try await reload()
                } }.buttonStyle(ZovaPrimary())
            }
        }.disabled(store.busy)
    }
    private func seriesCard(_ series: JSONValue) -> some View {
        ZovaCard {
            Text(series["spec"]["frequency"].string.capitalized + " " + series["spec"]["mode"].string + " drafts").font(.headline)
            Text(series["status"].string.capitalized + " · " + series["spec"]["timezone"].string).font(.caption)
            if series["status"].string != "cancelled" {
                HStack {
                    Button(series["status"].string == "paused" ? "Resume" : "Pause") { change(series, series["status"].string == "paused" ? "resume" : "pause") }
                    Button("Cancel series", role: .destructive) { change(series, "cancel") }
                }
                if series["status"].string == "active" && series["spec"]["mode"].string == "repeat" {
                    Button("Review repeat schedule") { run { repeatID = series["id"].int; repeatReview = try await store.request("/api/series/\(repeatID)/review", method: "POST", body: .object(["revision": series["revision"]])) } }
                }
            }
            ForEach(series["occurrences"].array, id: \.["id"].int) { item in
                VStack(alignment: .leading, spacing: 8) {
                    Text((ProductLinks.date(item["due_at"].string).map { ProductLinks.displayDate($0, timezone: series["spec"]["timezone"].string) } ?? item["due_at"].string) + " · " + item["status"].string).font(.caption)
                    if series["status"].string == "active" && item["status"].string != "cancelled" {
                        HStack {
                            Button(item["draft_id"].int > 0 ? "Open draft" : "Start draft") { run {
                                let reply = item["draft_id"].int > 0 ? JSONValue.object(["draft_id": item["draft_id"]]) : try await store.request("/api/series/occurrences/\(item["id"].int)/draft", method: "POST", body: .object([:]))
                                try await store.openDraft(reply["draft_id"].int); dismiss()
                            } }
                            Menu("More") {
                                Button("Change time") { occurrence = item; occurrenceRevision = series["revision"].int; occurrenceTimezone = series["spec"]["timezone"].string; movedDate = ProductLinks.date(item["due_at"].string) ?? Date(); future = false }
                                Button("Cancel occurrence", role: .destructive) { run { _ = try await store.request("/api/series/occurrences/\(item["id"].int)/cancel", method: "POST", body: .object(["revision": series["revision"]])); try await reload() } }
                            }
                        }.font(.caption)
                    }
                }.padding(.top, 8)
            }
        }.disabled(store.busy)
    }
    private func specification() -> JSONValue {
        let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd'T'HH:mm"; formatter.timeZone = TimeZone(identifier: store.timezone)
        return .object(["draft_id": .integer(store.draft.id ?? 0), "request_key": .string(requestKey), "start": .string(formatter.string(from: start)), "timezone": .string(store.timezone), "frequency": .string(frequency), "weekdays": .array(weekdays.sorted().map { .integer($0) }), "count": .integer(count), "mode": .string(mode)])
    }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
    private func reload() async throws { store.series = try await store.request("/api/series").array }
    private func change(_ series: JSONValue, _ action: String) { run { _ = try await store.request("/api/series/\(series["id"].int)/state", method: "POST", body: .object(["revision": series["revision"], "action": .string(action)])); try await reload() } }
}
