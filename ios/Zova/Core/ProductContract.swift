import Foundation

/// JSON fields are retained when editing existing drafts; unknown workspace
/// fields must not be silently discarded by a newer/older native client.
enum JSONValue: Codable, Equatable, Sendable {
    case object([String: JSONValue]), array([JSONValue]), string(String), number(Double), bool(Bool), null
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode([JSONValue].self) { self = .array(v) }
        else { self = .object(try c.decode([String: JSONValue].self)) }
    }
    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .object(let v): try c.encode(v)
        case .array(let v): try c.encode(v)
        case .string(let v): try c.encode(v)
        case .number(let v): try c.encode(v)
        case .bool(let v): try c.encode(v)
        case .null: try c.encodeNil()
        }
    }
    subscript(_ key: String) -> JSONValue {
        get { object[key] ?? .null }
        set { var values = object; values[key] = newValue; self = .object(values) }
    }
    var object: [String: JSONValue] { if case .object(let v) = self { return v }; return [:] }
    var array: [JSONValue] { if case .array(let v) = self { return v }; return [] }
    var string: String { if case .string(let v) = self { return v }; return "" }
    var int: Int { if case .number(let v) = self, v.isFinite, v >= Double(Int.min), v < Double(Int.max) { return Int(v) }; return 0 }
    var bool: Bool { if case .bool(let v) = self { return v }; return false }
    var strings: [String] { array.compactMap { if case .string(let v) = $0 { return v }; return nil } }
    var isNull: Bool { self == .null }
    static func strings(_ values: [String]) -> JSONValue { .array(values.map { .string($0) }) }
    static func integer(_ value: Int) -> JSONValue { .number(Double(value)) }
    func encoded() throws -> Data { try JSONEncoder().encode(self) }
}

enum SocialPlatform: String, CaseIterable, Identifiable {
    case x, instagram, facebook, tiktok
    var id: String { rawValue }
    var title: String { ["x": "X", "instagram": "Instagram", "facebook": "Facebook", "tiktok": "TikTok"][rawValue]! }
}

struct ProductError: LocalizedError {
    let status: Int
    let code: String
    let message: String
    var errorDescription: String? { message }
}

struct ProductDraft: Equatable {
    var id: Int?
    var revision = 0
    var status = "draft"
    var title = ""
    var brief = ""
    var instruction = ""
    var threadLength = 1
    var variants: JSONValue = .object([:])
    var workspace: JSONValue = .object([:])
    var planned: JSONValue = .null
    var editable: Bool { ["draft", "failed", "partial", "cancelled"].contains(status) }
    var selected: [String] {
        get { workspace["selected_platforms"].strings }
        set { workspace["selected_platforms"] = .strings(newValue); workspace["platform_selection_explicit"] = .bool(true) }
    }
    var composer: String {
        get { workspace["composer"].string }
        set { workspace["composer"] = .string(newValue) }
    }
    var media: [JSONValue] { workspace["media"].array }
    var conversation: [JSONValue] {
        get { workspace["conversation"].array }
        set { workspace["conversation"] = .array(newValue) }
    }
    var active: String {
        get { workspace["active_platform"].string.isEmpty ? selected.first ?? "x" : workspace["active_platform"].string }
        set { workspace["active_platform"] = .string(newValue) }
    }
    var mediaIDs: JSONValue { .array(media.map { $0["id"] }) }
    init() { }
    init(_ value: JSONValue) {
        id = value["id"].int > 0 ? value["id"].int : nil
        revision = value["revision"].int; status = value["status"].string
        title = value["display_title"].string; brief = value["brief"].string
        instruction = value["instruction"].string; threadLength = max(1, value["thread_length"].int)
        variants = value["variants"]; workspace = value["workspace"]; planned = value["planned"]
        if workspace["selected_platforms"].strings.isEmpty && !workspace["platform_selection_explicit"].bool {
            let available = Set(value["platforms"].strings + variants.object.keys)
            selected = SocialPlatform.allCases.map(\.rawValue).filter { available.contains($0) }
        }
        if !variants.object.isEmpty && variants[active].isNull { active = selected.first(where: { !variants[$0].isNull }) ?? variants.object.keys.sorted().first ?? "x" }
    }
    var payload: JSONValue {
        .object(["brief": .string(brief), "instruction": .string(instruction),
                 "platforms": .strings(SocialPlatform.allCases.map(\.rawValue).filter { variants.object[$0] != nil }),
                 "variants": variants, "workspace": workspace, "revision": .integer(revision),
                 "thread_length": .integer(threadLength)])
    }
    mutating func addHistory() {
        let history = Array((workspace["text_history"].array + [variants]).suffix(3))
        workspace["text_history"] = .array(history)
    }
    mutating func undo() {
        var history = workspace["text_history"].array
        if let previous = history.popLast() { variants = previous; workspace["text_history"] = .array(history) }
    }
}

enum ProductLinks {
    static func localDate(_ value: String, timezone: String) -> Date? {
        let formatter = DateFormatter(); formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm"; formatter.isLenient = false
        formatter.timeZone = TimeZone(identifier: timezone) ?? TimeZone(secondsFromGMT: 0)
        return formatter.date(from: String(value.prefix(16)))
    }
    static func displayDate(_ date: Date, timezone: String, time: Bool = true) -> String {
        let formatter = DateFormatter(); formatter.dateStyle = .medium; formatter.timeStyle = time ? .short : .none
        formatter.timeZone = TimeZone(identifier: timezone) ?? TimeZone(secondsFromGMT: 0)
        return formatter.string(from: date)
    }
    static func external(_ text: String) -> URL? {
        guard let url = URL(string: text), url.scheme == "https", url.host != nil,
              url.user == nil, url.password == nil else { return nil }
        return url
    }
    static func query(_ value: String) -> String {
        value.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? ""
    }
    static func date(_ value: String) -> Date? {
        let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        for candidate in [value, value + "Z"] {
            f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = f.date(from: candidate) { return date }
            f.formatOptions = [.withInternetDateTime]
            if let date = f.date(from: candidate) { return date }
        }
        return nil
    }
}
