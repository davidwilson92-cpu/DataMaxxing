import SwiftUI

struct NativeScheduleView: View {
    @EnvironmentObject var store: ProductStore
    @ScaledMetric(relativeTo: .caption) private var dayWidth: CGFloat = 44
    @ScaledMetric(relativeTo: .caption) private var dayHeight: CGFloat = 58
    @ScaledMetric(relativeTo: .caption2) private var weekdayHeight: CGFloat = 32
    @ScaledMetric(relativeTo: .callout) private var dayBadge: CGFloat = 28
    @State private var calendarMode = true
    @State private var month = Date()
    @State private var selectedDay: Date?
    @State private var monthRows: [JSONValue] = []
    @State private var summary: JSONValue = .null
    @State private var search = ""
    @State private var filter = "all"
    @State private var selected: JSONValue = .null
    @State private var recurring = false
    private var calendar: Calendar { var c = Calendar(identifier: .gregorian); c.firstWeekday = 2; c.timeZone = TimeZone(identifier: store.timezone) ?? .current; return c }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                NativeAdaptiveRow {
                    Text("Schedule").font(.title2.bold()); Spacer()
                    Button("+ New post") { run { try await store.newPost() } }.font(.subheadline.bold()).buttonStyle(.borderedProminent).tint(ZovaDesign.purple).frame(minHeight: 44)
                }
                if summary["unconfirmed"].int > 0 {
                    Button("Check publication results before retrying →") { calendarMode = false; filter = "awaiting_results"; reload() }.font(.caption).foregroundStyle(.orange)
                }
                if summary["overdue"].int > 0 { Text("\(summary["overdue"].int) overdue deliveries. Check their status; pending does not mean published.").font(.caption).foregroundStyle(.secondary) }
                NativeAdaptiveRow(spacing: 12) {
                    sectionTab("Calendar", selected: calendarMode) { calendarMode = true }
                    sectionTab("Saved posts", selected: !calendarMode) { calendarMode = false; reload() }
                    Button("Recurring drafts") { recurring = true }.font(.caption).frame(minHeight: 44)
                }
                if store.busy && !store.backgroundSaving { ProgressView("Loading saved work…") }
                if calendarMode { calendarContent } else { savedContent }
            }.padding(18)
        }.task(id: store.selectedTab) { if store.selectedTab == 1 { await load() } }.refreshable { await load() }
            .sheet(isPresented: Binding(get: { !selected.isNull }, set: { if !$0 { selected = .null } })) {
                NativeScheduleEdit(row: selected) { try await refreshData() }.environmentObject(store)
            }
            .sheet(isPresented: $recurring) { NativeSeriesView().environmentObject(store) }
    }
    private func sectionTab(_ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) { Text(title).font(.subheadline.weight(selected ? .semibold : .regular)).frame(minHeight: 44).overlay(alignment: .bottom) { Rectangle().fill(selected ? ZovaDesign.purple : .clear).frame(height: 2) } }
            .foregroundStyle(selected ? ZovaDesign.purple : ZovaDesign.ink).accessibilityAddTraits(selected ? .isSelected : [])
    }
    private var calendarContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            NativeAdaptiveRow(spacing: 4) {
                HStack(spacing: 4) {
                    Button { moveMonth(-1) } label: { Image(systemName: "arrow.left").frame(width: 44, height: 44).contentShape(Rectangle()) }.accessibilityLabel("Previous month")
                    Text(monthTitle).font(.subheadline.bold()).fixedSize(horizontal: false, vertical: true)
                    Button { moveMonth(1) } label: { Image(systemName: "arrow.right").frame(width: 44, height: 44).contentShape(Rectangle()) }.accessibilityLabel("Next month")
                }
                HStack(spacing: 4) {
                    Button { month = Date(); selectedDay = nil; run { try await loadMonth() } } label: { Text("Today").font(.caption).frame(minWidth: 44, minHeight: 44).contentShape(Rectangle()) }
                    Button { reload() } label: { Image(systemName: "arrow.clockwise").frame(width: 44, height: 44).contentShape(Rectangle()) }.accessibilityLabel("Refresh schedule")
                }
            }.disabled(store.busy)
            Text("Times in " + store.timezone).font(.caption).foregroundStyle(.secondary)
            GeometryReader { geometry in
                ScrollView(.horizontal) {
                    calendarGrid.frame(width: max(geometry.size.width, dayWidth * 7))
                }.accessibilityIdentifier("schedule-calendar")
            }.frame(height: weekdayHeight + CGFloat(calendarRows) * dayHeight)
            NativeAdaptiveRow {
                Text(selectedDay.map { ProductLinks.displayDate($0, timezone: store.timezone, time: false) } ?? "Posts this month").font(.headline)
                if selectedDay != nil { Button("Show month") { selectedDay = nil }.font(.caption).frame(minHeight: 44) }
            }
            if deliveries.isEmpty && !store.busy {
                Text(selectedDay == nil ? "No posts scheduled this month." : "No posts scheduled for this day.").font(.callout).foregroundStyle(.secondary)
            }
            ForEach(deliveries, id: \.["id"].int) { row in delivery(row) }
            if monthRows.count >= 100 { Text("Showing up to 100 deliveries in this month. Use Saved posts to find other work.").font(.caption).foregroundStyle(.secondary) }
        }
    }
    private var savedContent: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                TextField("Search saved posts", text: $search).textFieldStyle(.roundedBorder).onSubmit { reload() }
                Button { reload() } label: { Image(systemName: "magnifyingglass").frame(width: 44, height: 44) }.accessibilityLabel("Search saved posts")
            }
            Picker("Status", selection: $filter) {
                Text("All statuses").tag("all"); Text("Drafts").tag("draft"); Text("Scheduled").tag("scheduled")
                Text("Published").tag("published"); Text("Needs review").tag("needs_review"); Text("Awaiting results").tag("awaiting_results")
            }.pickerStyle(.menu).onChange(of: filter) { _, _ in reload() }.disabled(store.busy)
            if store.drafts.isEmpty && !store.busy { Text(search.isEmpty && filter == "all" ? "Create a post in Studio. Save it or choose a time." : "No matching posts. Try another search.").font(.callout).foregroundStyle(.secondary) }
            ForEach(store.drafts, id: \.["id"].int) { row in
                NativeDraftRow(row: row, open: {
                    if row["status"].string == "scheduled" { try await findSchedule(row["id"].int) }
                    else { try await store.openDraft(row["id"].int) }
                }) { try await refreshData() }
            }
            if store.moreDrafts { Button("Load older posts") { run { try await store.loadDrafts(search: search, more: true, status: filter) } }.disabled(store.busy) }
        }
    }
    private var deliveries: [JSONValue] {
        monthRows.filter { row in selectedDay == nil || ProductLinks.date(row["scheduled_at"].string).map { calendar.isDate($0, inSameDayAs: selectedDay!) } == true }
    }
    private func delivery(_ row: JSONValue) -> some View {
        VStack(spacing: 14) {
            NativeAdaptiveRow(spacing: 12) {
                VStack(alignment: .leading, spacing: 5) {
                    if let date = ProductLinks.date(row["scheduled_at"].string) {
                        Text(shortDate(date, format: "d MMM")).font(.caption2)
                        Text(shortDate(date, format: "HH:mm")).font(.caption.bold())
                    }
                }.foregroundStyle(.secondary)
                VStack(alignment: .leading, spacing: 8) {
                    NativeAdaptiveRow { HStack { NativePlatformMark(platform: row["platform"].string, size: 20); Text(row["account_name"].string).font(.caption) }; Text(status(row["status"].string)).font(.caption2).foregroundStyle(.secondary) }
                    Text(row["title"].string).font(.subheadline.bold()).lineLimit(2)
                    if !row["excerpt"].string.isEmpty { Text(row["excerpt"].string).font(.caption).foregroundStyle(.secondary).lineLimit(3) }
                    Button(row["status"].string == "scheduled" ? "Manage schedule →" : "View results →") { selected = row }.font(.caption).frame(minHeight: 44)
                }
            }
            Divider()
        }
    }
    private var calendarRows: Int {
        let start = calendar.dateInterval(of: .month, for: month)!.start
        let padding = (calendar.component(.weekday, from: start) - 2 + 7) % 7
        return (padding + calendar.range(of: .day, in: .month, for: month)!.count + 6) / 7
    }
    private var calendarGrid: some View {
        let start = calendar.dateInterval(of: .month, for: month)!.start
        let count = calendar.range(of: .day, in: .month, for: month)!.count
        let padding = (calendar.component(.weekday, from: start) - 2 + 7) % 7
        let cells = ((padding + count + 6) / 7) * 7
        return LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 0), count: 7), spacing: 0) {
            ForEach(Array(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].enumerated()), id: \.offset) { _, title in
                Text(title).font(.caption2).foregroundStyle(.secondary).frame(maxWidth: .infinity).frame(height: weekdayHeight).background(ZovaDesign.pale).border(ZovaDesign.line.opacity(0.5), width: 0.5)
            }
            ForEach(0..<cells, id: \.self) { position in
                if position < padding || position >= padding + count {
                    Color.clear.frame(height: dayHeight).border(ZovaDesign.line.opacity(0.5), width: 0.5)
                } else {
                    let date = calendar.date(byAdding: .day, value: position - padding, to: start)!
                    let posts = monthRows.filter { ProductLinks.date($0["scheduled_at"].string).map { calendar.isDate($0, inSameDayAs: date) } == true }.count
                    let chosen = selectedDay.map { calendar.isDate($0, inSameDayAs: date) } ?? false
                    let today = calendar.isDateInToday(date)
                    Button { selectedDay = chosen ? nil : date } label: {
                        VStack(spacing: 2) {
                            Text(String(position - padding + 1)).font(.callout).frame(width: dayBadge, height: dayBadge).foregroundStyle(today ? .white : ZovaDesign.ink).background(today ? ZovaDesign.ink : .clear, in: Circle())
                            if posts > 0 { Text(String(posts)).font(.caption2.weight(.semibold)).foregroundStyle(ZovaDesign.purple) }
                        }.frame(maxWidth: .infinity).frame(height: dayHeight).background(chosen ? ZovaDesign.pale : .clear).border(ZovaDesign.line.opacity(0.5), width: 0.5).contentShape(Rectangle())
                    }.buttonStyle(.plain).accessibilityLabel(ProductLinks.displayDate(date, timezone: store.timezone, time: false) + ", \(posts) posts").accessibilityAddTraits(chosen ? .isSelected : []).accessibilityIdentifier("calendar-day-\(position - padding + 1)")
                }
            }
        }.clipShape(RoundedRectangle(cornerRadius: 10)).overlay(RoundedRectangle(cornerRadius: 10).stroke(ZovaDesign.line, lineWidth: 0.5))
    }
    private func status(_ value: String) -> String {
        ["unknown": "Unconfirmed", "publishing": "Sending", "queued": "Queued", "pending": "Processing"][value] ?? value.capitalized
    }
    private var monthTitle: String { shortDate(month, format: "MMMM yyyy") }
    private func shortDate(_ date: Date, format: String) -> String { let f = DateFormatter(); f.dateFormat = format; f.timeZone = calendar.timeZone; return f.string(from: date) }
    private func run(_ work: @escaping @MainActor () async throws -> Void) { Task { await store.perform(work) } }
    private func reload() { Task { await load() } }
    private func load() async { await store.perform { try await refreshData() } }
    private func refreshData() async throws {
        summary = try await store.request("/api/native/schedule-summary")
        if !calendarMode { try await store.loadDrafts(search: search, status: filter) }
        try await loadMonth()
    }
    private func loadMonth() async throws {
        let interval = calendar.dateInterval(of: .month, for: month)!, format = ISO8601DateFormatter()
        monthRows = try await store.request("/api/schedules?from=" + ProductLinks.query(format.string(from: interval.start)) + "&to=" + ProductLinks.query(format.string(from: interval.end))).array
    }
    private func findSchedule(_ id: Int) async throws {
        let rows = try await store.request("/api/schedules?draft_id=\(id)").array
        guard let row = rows.first(where: { $0["status"].string == "scheduled" }) ?? rows.first, let date = ProductLinks.date(row["scheduled_at"].string) else { throw ZovaFailure.server("No upcoming delivery found. Refresh to check its results.") }
        month = date; selectedDay = date; calendarMode = true; try await loadMonth(); selected = row
    }
    private func moveMonth(_ offset: Int) { guard !store.busy else { return }; month = calendar.date(byAdding: .month, value: offset, to: month)!; selectedDay = nil; run { try await loadMonth() } }
}
