import SwiftUI

/// Inline campaign tools; proposals are persisted server-side until explicitly applied.
struct CampaignActionsView: View {
    let row: JSONValue
    let working: Bool
    @Binding var calendarView: Bool
    @Binding var sortBy: String
    let allCampaigns: () -> Void
    let rename: () -> Void
    let refresh: () async -> Void
    let request: (String, JSONValue) async -> Bool
    @Environment(\.dynamicTypeSize) private var textSize
    @State private var action = ""
    @State private var name = ""
    @State private var feedback = ""
    @State private var start = Date().addingTimeInterval(86400)
    @State private var count = 2
    @State private var reuseKey = UUID().uuidString
    private var paused: Bool { row["state"].string == "paused" }
    private var titles: [String:String] { ["pause":"Pause campaign", "resume":"Resume campaign", "move":"Move remaining dates", "reuse":"Reuse campaign", "extend":"Add posts", "improve":"Improve remaining posts"] }
    private var zone: TimeZone { TimeZone(identifier:row["brief"]["timezone"].string) ?? .current }
    private var hasDate: Bool { ["move","reuse","extend"].contains(action) }
    private var aiAction: Bool { ["improve","extend"].contains(action) }
    private var canImprove: Bool {
        row["posts"].array.contains { post in
            ["", "draft", "scheduled"].contains(post["status"].string) &&
            (row["draft_ids"].array.isEmpty || post["simple"].bool)
        }
    }

    var body: some View {
        VStack(alignment:.leading,spacing:8) {
            VStack(spacing:4) {
                if textSize.isAccessibilitySize {
                    VStack(alignment:.leading,spacing:4) {
                        allButton
                        HStack { improveButton; Spacer(minLength:0); actionsMenu }
                    }
                } else {
                    HStack(spacing:8) {
                        allButton
                        Spacer(minLength:0)
                        improveButton
                        actionsMenu
                    }
                }
                Divider().overlay(Color.white.opacity(0.16))
                ViewThatFits(in:.horizontal) {
                    HStack(spacing:8) { viewPicker; sortMenu }
                    VStack(alignment:.leading,spacing:4) { viewPicker; sortMenu }
                }
            }.font(.subheadline).foregroundStyle(.white).tint(.white)
                .padding(.horizontal,10).padding(.vertical,4)
                .background(LinearGradient(colors:[.black,Color(red:0.13,green:0.08,blue:0.18)],startPoint:.topLeading,endPoint:.bottomTrailing),in:RoundedRectangle(cornerRadius:12))
                .overlay(RoundedRectangle(cornerRadius:12).stroke(Color.white.opacity(0.22)))
                .environment(\.colorScheme,.dark)
            if paused { Label("Paused · drafts kept",systemImage:"pause.circle").font(.caption) }
            if !action.isEmpty { editor }
        }
        if !row["suggestion"].isNull { proposal }
    }
    private var allButton: some View {
        Button(action:allCampaigns) {
            Label("All campaigns",systemImage:"chevron.left").frame(minHeight:44)
        }.accessibilityIdentifier("campaign-all")
    }
    private var viewPicker: some View {
        Group {
            if textSize.isAccessibilitySize {
                VStack(spacing:2) {
                    viewButton("Previews",calendar:false)
                    viewButton("Calendar",calendar:true)
                }
            } else {
                HStack(spacing:2) {
                    viewButton("Previews",calendar:false)
                    viewButton("Calendar",calendar:true)
                }
            }
        }.padding(3).background(Color(white:0.12),in:RoundedRectangle(cornerRadius:9))
    }
    private func viewButton(_ title:String,calendar:Bool) -> some View {
        Button {calendarView=calendar} label: {
            Text(title).fontWeight(calendarView==calendar ? .semibold : .regular)
                .frame(maxWidth:.infinity,minHeight:44)
                .padding(.horizontal,8)
                .background(calendarView==calendar ? Color(white:0.25) : .clear,in:RoundedRectangle(cornerRadius:7))
        }.accessibilityAddTraits(calendarView==calendar ? [.isSelected] : [])
    }
    private var sortMenu: some View {
        Menu {
            Picker("Sort by",selection:$sortBy) {
                ForEach(["Date","Platform","Media type"],id:\.self){Text($0)}
            }
        } label: { Label(sortBy,systemImage:"arrow.up.arrow.down").fixedSize().frame(minHeight:44) }
            .accessibilityLabel("Sort by").accessibilityValue(sortBy)
    }
    @ViewBuilder private var improveButton: some View {
        if canImprove {
            Button { begin("improve") } label: { Label("Improve",systemImage:"sparkles").frame(minHeight:44) }
                .accessibilityLabel("Improve remaining posts")
                .accessibilityIdentifier("campaign-improve")
        }
    }
    private var actionsMenu: some View {
        Menu {
            Button("Rename campaign",systemImage:"pencil",action:rename)
            Button(paused ? "Resume campaign" : "Pause campaign",systemImage:paused ? "play" : "pause") { begin(paused ? "resume" : "pause") }
            Button("Move remaining dates",systemImage:"calendar") { begin("move") }
            Button("Add posts",systemImage:"plus") { begin("extend") }
            Button("Reuse campaign",systemImage:"doc.on.doc") { begin("reuse") }
        } label: { Image(systemName:"ellipsis.circle").frame(minWidth:44,minHeight:44) }
        .accessibilityLabel("Campaign actions")
        .accessibilityIdentifier("campaign-actions")
    }
    private func begin(_ value:String) {
        Task {
            await refresh()
            action=value; name=String((campaignName(row)+" copy").prefix(80));feedback="";reuseKey=UUID().uuidString
            let last=row["dates"].array.compactMap {ProductLinks.date($0["utc"].string)}.max() ?? Date()
            start=max(Date().addingTimeInterval(86400), value=="extend" ? last.addingTimeInterval(86400) : Date().addingTimeInterval(86400))
        }
    }
    @ViewBuilder private var editor: some View {
        VStack(alignment:.leading,spacing:12) {
            Text(titles[action] ?? "Campaign").font(.headline)
            Text(note).font(.caption).foregroundStyle(.secondary)
            if action=="reuse" { TextField("Campaign name",text:$name).textFieldStyle(.roundedBorder).accessibilityLabel("Copy campaign name") }
            if hasDate {
                DatePicker("First post",selection:$start,in:Date()...,displayedComponents:[.date,.hourAndMinute]).environment(\.timeZone,zone)
                Text(zone.identifier).font(.caption).foregroundStyle(.secondary)
            }
            if action=="extend" { Stepper("\(count) additional posts",value:$count,in:1...10) }
            if aiAction { TextField("Anything to change? Optional",text:$feedback,axis:.vertical).textFieldStyle(.roundedBorder) }
            ViewThatFits(in:.horizontal) {
                HStack { submitButton; Button("Cancel"){action=""} }
                VStack(alignment:.leading) { submitButton; Button("Cancel"){action=""} }
            }
        }.padding(12).background(ZovaDesign.pale,in:RoundedRectangle(cornerRadius:12))
    }
    private var note:String {
        switch action {
        case "pause": return "Stops remaining scheduled posts. Resume keeps them as drafts for final review."
        case "resume": return "Posts remain drafts until you review and schedule them."
        case "move": return "Moves remaining posts together. Scheduled posts return to drafts for final review."
        case "reuse": return "Copies captions and media into a new plan. Check date-sensitive wording."
        case "extend": return "Preview follow-ups using your campaign, strategy, voice and available results."
        default: return "Preview caption changes. Applying them returns scheduled posts to drafts for final approval."
        }
    }
    private var submitButton: some View {
        Button(aiAction ? "Preview changes" : action=="reuse" ? "Create copy" : titles[action] ?? "Save") {
            let format=DateFormatter();format.locale=Locale(identifier:"en_US_POSIX");format.timeZone=zone;format.dateFormat="yyyy-MM-dd'T'HH:mm"
            let local=JSONValue.string(format.string(from:start)),base="/api/campaigns/\(row["id"].int)"
            var path=base+"/control"
            var body:JSONValue = .object(["revision":row["revision"],"action":.string(action),"snapshot":row["control_snapshot"],"start":local])
            if action=="reuse" {
                path=base+"/reuse";body = .object(["revision":row["revision"],"name":.string(name),"start":local,"request_key":.string(reuseKey)])
            } else if aiAction {
                path="/api/ai/campaigns/\(row["id"].int)/improve"
                body = .object(["revision":row["revision"],"mode":.string(action),"feedback":.string(feedback),"count":.integer(count),"start":local])
            }
            Task { if await request(path,body) {action=""} }
        }.buttonStyle(ZovaPrimary()).disabled(working || (action=="reuse" && (name.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty || name.count>80)))
    }
    @ViewBuilder private var proposal: some View {
        let suggestion=row["suggestion"],posts=suggestion["posts"].array
        Section(suggestion["mode"].string=="extend" ? "New follow-ups" : "Proposed improvements") {
            Text("\(posts.count) \(posts.count == 1 ? "post" : "posts") · " + suggestion["basis"].string).font(.caption).foregroundStyle(.secondary)
            if suggestion["positions"].array.contains(where: { $0.int<row["posts"].array.count && row["posts"].array[$0.int]["status"].string=="scheduled" }) {
                Text("Applying changes unschedules these posts. Review them again before publishing.").font(.callout)
            }
            ForEach(posts.indices,id:\.self) { n in
                let post=posts[n],i=suggestion["positions"].array[n].int
                VStack(alignment:.leading,spacing:8) {
                    CampaignStrip(platform:post["platform"].string,date:ProductLinks.displayDate(ProductLinks.date(suggestion["dates"].array[n]["utc"].string) ?? start,timezone:zone.identifier))
                    Text(post["caption"].string)
                    ForEach(campaignAssets(row,post),id:\.["id"].int) {asset in CampaignMediaTile(asset:asset,height:100)}
                    if i<row["posts"].array.count {
                        DisclosureGroup("Original caption") {Text(row["posts"].array[i]["caption"].string)}.font(.subheadline)
                    }
                }
            }
            Button("Apply changes") { decide("apply") }.buttonStyle(ZovaPrimary())
                .accessibilityIdentifier("campaign-apply-improvements")
            Button("Keep originals") { decide("discard") }
        }
    }
    private func decide(_ value:String) {
        Task { _ = await request("/api/campaigns/\(row["id"].int)/suggestion",.object(["revision":row["revision"],"action":.string(value)])) }
    }
}
