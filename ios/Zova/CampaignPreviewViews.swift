import SwiftUI

func campaignName(_ row: JSONValue) -> String {
    row["name"].string.isEmpty ? String(row["brief"]["idea"].string.prefix(80)) : row["name"].string
}

func campaignAssets(_ row: JSONValue, _ post: JSONValue) -> [JSONValue] {
    let ids = post["media_ids"].isNull ? [post["asset_id"]] : post["media_ids"].array
    return ids.filter { $0.int > 0 }.map { id in
        let original = row["assets"].array.first { $0["id"] == id } ?? .null
        let name = original["name"].string
        let video = ["mov","mp4","webm"].contains((name as NSString).pathExtension.lowercased())
        return .object(["id":id,"filename":.string(name),"kind":original["kind"].isNull ? .string(video ? "video" : "image") : original["kind"]])
    }
}

struct CampaignMediaTile: View {
    @EnvironmentObject var store: ProductStore
    let asset: JSONValue
    @State private var thumbnail: UIImage?
    @State private var viewing = false
    var body: some View {
        Button { viewing = true } label: {
            ZStack {
                Color(.secondarySystemBackground)
                if let thumbnail { Image(uiImage: thumbnail).resizable().scaledToFit() }
                if asset["kind"].string == "video" {
                    Image(systemName:"play.circle.fill").font(.largeTitle).symbolRenderingMode(.palette).foregroundStyle(.white,.black)
                } else if thumbnail == nil { Image(systemName:"photo") }
            }.frame(maxWidth:.infinity).frame(height:180).clipShape(RoundedRectangle(cornerRadius:10))
        }.accessibilityLabel("Preview " + asset["filename"].string)
        .task(id:asset["id"].int) {
            do {
                let url = try await store.assetFile(asset, thumbnail:true)
                defer { NativeMediaFiles.remove(url) }
                try Task.checkCancellation()
                thumbnail = UIImage(contentsOfFile:url.path)
            } catch { thumbnail = nil }
        }.sheet(isPresented:$viewing) {
            VStack { NativeSheetHeader(title:"Media preview"); NativeAssetPreview(asset:asset) }.padding()
        }
    }
}

struct CampaignStrip: View {
    let platform: String
    let date: String
    var body: some View {
        let colors: [Color] = switch platform {
        case "instagram": [.purple,Color(red:0.63,green:0.17,blue:0.36)]
        case "facebook": [Color(red:0.07,green:0.33,blue:0.68)]
        default: [.black]
        }
        NativeAdaptiveRow {
            HStack {
                NativePlatformMark(platform: platform,size:19).padding(4).background(.white,in:RoundedRectangle(cornerRadius:6))
                Text(SocialPlatform(rawValue:platform)?.title ?? platform).font(.headline.weight(.bold))
            }
            Spacer(); Text(date).font(.caption.bold())
        }.padding(10).foregroundStyle(.white).background(LinearGradient(colors:colors,startPoint:.leading,endPoint:.trailing))
        .overlay(alignment:.top){if platform=="tiktok" { Rectangle().fill(Color.cyan).frame(height:2) }}
    }
}

struct CampaignCalendar: View {
    let days: [String]
    @Binding var selected: String
    @State private var month: Date
    private let calendar: Calendar
    private let formatter: DateFormatter
    init(days:[String], selected:Binding<String>) {
        self.days=days; _selected=selected
        let utc=TimeZone(secondsFromGMT:0)!
        var cal=Calendar(identifier:.gregorian);cal.timeZone=utc; calendar=cal
        let f=DateFormatter();f.locale=Locale(identifier:"en_US_POSIX");f.timeZone=utc;f.dateFormat="yyyy-MM-dd";formatter=f
        let first=f.date(from:selected.wrappedValue) ?? Date()
        _month=State(initialValue:cal.date(from:cal.dateComponents([.year,.month],from:first)) ?? first)
    }
    private var monthTitle: String {
        let f=DateFormatter(); f.timeZone=calendar.timeZone; f.dateFormat="LLLL yyyy"; return f.string(from:month)
    }
    private func move(_ delta:Int) {
        guard let next=calendar.date(byAdding:.month,value:delta,to:month) else {return}
        month=next
        let key=formatter.string(from:next)
        selected=days.sorted().first(where:{$0.hasPrefix(String(key.prefix(7)))}) ?? key
    }
    var body: some View {
        VStack {
            HStack {
                Button {move(-1)} label:{Image(systemName:"chevron.left").frame(width:44,height:44)}.accessibilityLabel("Previous month")
                Spacer(); Text(monthTitle).font(.headline);Spacer()
                Button {move(1)} label:{Image(systemName:"chevron.right").frame(width:44,height:44)}.accessibilityLabel("Next month")
            }
            LazyVGrid(columns:Array(repeating:GridItem(.flexible(),spacing:1),count:7),spacing:2) {
                ForEach(["M","Tu","W","Th","F","Sa","Su"],id:\.self){ Text($0).font(.caption) }
                ForEach(0..<((calendar.component(.weekday,from:month)+5)%7),id:\.self){_ in Color.clear.frame(height:1)}
                ForEach(0..<(calendar.range(of:.day,in:.month,for:month)?.count ?? 0),id:\.self){i in
                    let key=formatter.string(from:calendar.date(byAdding:.day,value:i,to:month)!)
                    let count=days.filter{$0==key}.count
                    Button {selected=key} label:{
                        VStack(spacing:1){ Text(String(i+1));if count>0 {Text(String(count)).font(.caption2.bold())} }
                            .frame(maxWidth:.infinity,minHeight:44).background(selected==key ? ZovaDesign.pale : .clear,in:RoundedRectangle(cornerRadius:6))
                    }.disabled(count==0).accessibilityLabel("\(key), \(count) posts")
                }
            }
            if !days.contains(selected){Text("No posts this month.").font(.caption)}
        }
    }
}
