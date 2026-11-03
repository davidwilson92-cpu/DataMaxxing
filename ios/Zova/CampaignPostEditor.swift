import SwiftUI

struct CampaignPostEditor: View {
    let row: JSONValue
    let index: Int
    let errorMessage: String
    let working: Bool
    let save: (JSONValue) async -> Void
    @State private var platform: String
    @State private var caption: String
    @State private var asset: Int
    @State private var date: Date
    @State private var expanded = false

    init(row: JSONValue, index: Int, errorMessage: String, working: Bool, save: @escaping (JSONValue) async -> Void) {
        self.row = row; self.index = index; self.save = save; self.errorMessage = errorMessage; self.working = working
        let post = row["posts"].array[index]
        _platform = State(initialValue: post["platform"].string)
        _caption = State(initialValue: post["caption"].string)
        _asset = State(initialValue: post["asset_id"].int)
        _date = State(initialValue: ProductLinks.date(row["dates"].array[index]["utc"].string) ?? Date())
    }
    private var zone: TimeZone { TimeZone(identifier: row["brief"]["timezone"].string) ?? .current }
    var body: some View {
        Button("Edit post") {
            let post = row["posts"].array[index]
            platform = post["platform"].string; caption = post["caption"].string; asset = post["asset_id"].int
            date = ProductLinks.date(row["dates"].array[index]["utc"].string) ?? date
            expanded = true
        }.sheet(isPresented: $expanded) {
            NavigationStack { Form {
                NativeField(title: "Caption", text: $caption, lines: 3)
                Picker("Platform", selection: $platform) {
                    ForEach(SocialPlatform.allCases) { Text($0.title).tag($0.rawValue) }
                }
                Picker("Media", selection: $asset) {
                    Text("No attachment").tag(0)
                    ForEach(row["assets"].array, id: \.["id"].int) { Text($0["name"].string).tag($0["id"].int) }
                    if asset != 0 && !row["assets"].array.contains(where: { $0["id"].int == asset }) {
                        Text("Current attachment").tag(asset)
                    }
                }
                DatePicker("Planned time", selection: $date).environment(\.timeZone, zone)
                if !errorMessage.isEmpty { Text(errorMessage).font(.caption) }
            }.disabled(working).navigationTitle("Edit post").navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { expanded = false }.disabled(working) }
                ToolbarItem(placement: .confirmationAction) {
                Button("Save changes") {
                    let formatter = DateFormatter()
                    formatter.locale = Locale(identifier: "en_US_POSIX"); formatter.timeZone = zone
                    formatter.dateFormat = "yyyy-MM-dd'T'HH:mm"
                    let post = row["posts"].array[index]
                    Task { await save(.object(["revision":row["revision"], "draft_revision":post["draft_revision"],
                        "series_revision":post["series_revision"], "platform":.string(platform), "caption":.string(caption),
                        "asset_id":asset == 0 ? .null : .integer(asset), "local_time":.string(formatter.string(from:date))])) }
                }
                }
            }
            }.disabled(working).interactiveDismissDisabled(working)
        }
    }
}

struct CampaignTimeEditor: View {
    let zone: TimeZone
    let save: (String) async -> Void
    @State private var time: Date

    init(when: String, zone: String, save: @escaping (String) async -> Void) {
        self.zone = TimeZone(identifier: zone) ?? .current; self.save = save
        _time = State(initialValue: ProductLinks.date(when) ?? Date())
    }
    var body: some View {
        DisclosureGroup("Change time") {
            DatePicker("New time", selection: $time).environment(\.timeZone, zone)
            Button("Reschedule") {
                let formatter = DateFormatter()
                formatter.locale = Locale(identifier: "en_US_POSIX"); formatter.timeZone = zone
                formatter.dateFormat = "yyyy-MM-dd'T'HH:mm"
                Task { await save(formatter.string(from: time)) }
            }
        }
    }
}
