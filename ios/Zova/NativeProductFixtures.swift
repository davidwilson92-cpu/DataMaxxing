#if DEBUG
import Foundation
import UIKit

/// Compiled out of release. Disposable, offline transport for simulator parity
/// evidence. It cannot contact a real user, AI service or publishing provider.
final class NativeProductFixtures: URLProtocol {
    static let lock = NSLock()
    static var saved: [Int: JSONValue] = [:]
    static var batch = 0
    static var storedStrategy: JSONValue = .null
    static var storedProposal: JSONValue = .null
    static var strategyRevision = 1
    static var primaryPlatform = "instagram"
    static var schedule: JSONValue = .null
    static func reset(tiktok: Bool = false) {
        lock.lock(); defer { lock.unlock() }
        primaryPlatform = tiktok ? "tiktok" : "instagram"
        saved = [24: draft(24)]; batch = 0
        storedStrategy = strategy; storedProposal = .null; strategyRevision = 1
        let date = Calendar.current.date(byAdding: .day, value: 1, to: Date())!
        schedule = .object(["id": .integer(1), "draft_id": .integer(24), "draft_revision": .integer(1), "platform": .string("instagram"), "title": .string("Beginner pottery class"), "account_name": .string("Pottery Studio"), "status": .string("scheduled"), "scheduled_at": .string(ISO8601DateFormatter().string(from: date)), "updated_at": .string("2026-10-27T10:00:00Z")])
    }
    static func draft(_ id: Int) -> JSONValue {
        .object(["id": .integer(id), "revision": .integer(1), "status": .string("draft"), "display_title": .string("Meet the maker"), "title": .string("Meet the maker"), "brief": .string("The story behind our small pottery studio."), "instruction": .string(""), "thread_length": .integer(1), "platforms": .strings([primaryPlatform]), "variants": .object([primaryPlatform: .object(["posts": .strings(["New to pottery? Start with a small piece of clay and give yourself time to learn. What would you like to try making?"])])]), "workspace": .object(["selected_platforms": .strings([primaryPlatform]), "active_platform": .string(primaryPlatform), "media": .array([]), "media_asset_ids": .array([]), "composer": .string(""), "conversation": .array([.object(["role": .string("user"), "content": .string("The story behind our small pottery studio.")])])])])
    }
    static var strategy: JSONValue { .object(["goal": .string("Generate pottery class enquiries"), "description": .string("I run a pottery studio in Leeds for curious beginners. I want more weekend bookings."), "content_direction": .string("Studio moments, simple tips, new classes. Two videos a week. Keep it friendly."), "audience": .string("Local beginners"), "themes": .string("Beginner pottery tips, clay process, common questions"), "rhythm": .string("Two posts each week"), "platforms": .strings(["instagram"])]) }
    static func actions() -> JSONValue {
        .object(["revision": .integer(1), "history": .array([]), "items": .array(["Share one tip for centring clay", "Explain what beginners need for class", "Invite questions about starting pottery"].enumerated().map { index, title in
            .object(["id": .integer(batch * 3 + index + 1), "title": .string(title), "reason": .string("Help local beginners feel confident enough to try a pottery class."), "kind": .string("draft"), "platform": .string(primaryPlatform), "format": .string("post"), "brief": .string(title), "basis": .string("Strategy · Voice"), "strategy_context": strategy, "source": .null])
        })])
    }
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        let (status, value, headers) = Self.response(request)
        let data = (try? value.encoded()) ?? Data()
        client?.urlProtocol(self, didReceive: HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: nil, headerFields: ["Content-Type":"application/json"].merging(headers) { _, new in new })!, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data); client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() { }
    static func body(_ request: URLRequest) -> JSONValue {
        var data = request.httpBody ?? Data()
        if data.isEmpty, let stream = request.httpBodyStream {
            stream.open(); defer { stream.close() }; var buffer = [UInt8](repeating: 0, count: 4096)
            while stream.hasBytesAvailable { let size = stream.read(&buffer, maxLength: buffer.count); if size <= 0 { break }; data.append(contentsOf: buffer.prefix(size)) }
        }
        return (try? JSONDecoder().decode(JSONValue.self, from: data)) ?? .null
    }
    static func response(_ request: URLRequest) -> (Int, JSONValue, [String: String]) {
        lock.lock(); defer { lock.unlock() }
        let path = request.url!.path, input = body(request)
        func ok(_ value: JSONValue) -> (Int, JSONValue, [String: String]) { (200, value, [:]) }
        if path == "/api/v1/native-config" { return ok(.object(["enabled": .bool(true), "redirect_uri": .string("https://zova-social.com/mobile/callback")])) }
        if path == "/api/v1/native-handoff" { return ok(.object(["ticket": .string(String(repeating: "t", count: 64))])) }
        if path == "/api/v1/native-web-session" { return (200, .object(["destination": .string("/studio")]), ["Set-Cookie":"nova_session=ios.synthetic-fixture; Path=/; Max-Age=900; Secure; HttpOnly; SameSite=Lax"]) }
        if path == "/api/native/account" {
            return ok(.object(["presentation_version": .integer(1), "profile": .object(["id": .integer(1), "name": .string("Synthetic creator"), "email": .string("creator@example.test"), "email_verified": .bool(true)]), "brand": .object(["id": .integer(0), "name": .string("My pottery studio"), "choices": .array([.object(["id": .integer(0), "name": .string("My pottery studio")])])]), "voice": .object(["writing_tone": .string("Warm and practical"), "audience": .string("Local beginners"), "topics": .string("Pottery"), "timezone": .string("Europe/London"), "preferred_post_length": .integer(220)]), "connections": .array([.object(["id": .integer(1), "platform": .string(primaryPlatform), "name": .string("Pottery Studio"), "username": .string("pottery")])]), "ai": .object(["allowed": .bool(true), "required": .bool(true), "version": .string("2026-10-19")])]))
        }
        if path == "/api/studio/intro/claim" { return ok(.object(["show": .bool(false)])) }
        if path == "/api/native/schedule-summary" { return ok(.object(["drafts": .integer(saved.count), "scheduled": .integer(1), "overdue": .integer(0), "unconfirmed": .integer(0)])) }
        if path == "/api/strategy" { return ok(.object(["revision": .integer(strategyRevision), "confirmed": storedStrategy, "defaults": strategy, "proposal": storedProposal])) }
        if path == "/api/strategy/actions" { return ok(actions()) }
        if path == "/api/strategy/recommend" { batch += 1; return ok(actions()) }
        if path == "/api/strategy/propose" {
            var next = storedStrategy; next["description"] = input["brief"]; next["content_direction"] = input["content_direction"]
            storedProposal = .object(["strategy": next, "assumptions": .array([])]); strategyRevision += 1
            return ok(.object(["revision": .integer(strategyRevision), "proposal": storedProposal]))
        }
        if path == "/api/strategy/confirm" {
            storedStrategy = input["strategy"]; storedProposal = .null; strategyRevision += 1
            return ok(.object(["revision": .integer(strategyRevision), "confirmed": storedStrategy]))
        }
        if path.hasPrefix("/api/strategy/actions/") && path.hasSuffix("/draft") { return ok(.object(["draft_id": .integer(24)])) }
        if path == "/api/drafts" {
            if request.httpMethod == "POST" { let id = (saved.keys.max() ?? 24) + 1; var value = draft(id); value["variants"] = .object([:]); value["workspace"] = .object([:]); saved[id] = value; return ok(.object(["id": .integer(id), "revision": .integer(1)])) }
            return ok(.array(saved.values.map { value in var row = value; row["title"] = .string(value["brief"].string); return row }.sorted { $0["id"].int > $1["id"].int }))
        }
        if path.hasPrefix("/api/drafts/"), let id = Int(path.split(separator: "/").last ?? "") {
            guard var value = saved[id] else { return (404, .object(["detail": .string("Draft not found")]), [:]) }
            if request.httpMethod == "PATCH" {
                guard input["revision"].int == value["revision"].int else { return (409, .object(["detail": .string("Synthetic draft revision mismatch: expected \(value["revision"].int), received \(input["revision"].int).")]), [:]) }
                for (key, field) in input.object { value[key] = field }; value["revision"] = .integer(value["revision"].int + 1); saved[id] = value
            }
            if request.httpMethod == "DELETE" { saved.removeValue(forKey: id); return (204, .null, [:]) }
            return ok(value)
        }
        if path == "/api/conversation/plan" { return ok(.object(["action": .string(input["message"].string.lowercased().contains("shorter") ? "rewrite" : "create"), "platforms": input["selected_platforms"], "brief": input["message"]])) }
        if path == "/api/ai/rewrite" { return ok(.object(["posts": .strings(["A little clay. A fresh start."])])) }
        if path == "/api/ai/generate" {
            let fresh = input["source_draft_id"].int > 0
            let id = fresh ? (saved.keys.max() ?? 24) + 1 : input["draft_id"].int
            if fresh, var source = saved[input["source_draft_id"].int] { source["id"] = .integer(id); source["revision"] = .integer(1); source["variants"] = .object([:]); saved[id] = source }
            guard var value = saved[id] else { return (404, .object(["detail": .string("Draft not found")]), [:]) }
            value["variants"] = .object(Dictionary(uniqueKeysWithValues: input["platforms"].strings.map { ($0, JSONValue.object(["posts": .strings(["New to pottery? Start with a small piece of clay and give yourself time to learn. What would you like to try making?"])])) }))
            value["brief"] = input["brief"]; value["revision"] = .integer(value["revision"].int + 1); value["workspace"]["pending_message"] = .string(""); saved[id] = value
            return ok(.object(["draft_id": .integer(id), "revision": value["revision"], "variants": value["variants"]]))
        }
        if path == "/api/schedules" {
            return ok(.array(schedule["status"].string == "scheduled" ? [schedule] : []))
        }
        if path == "/api/schedules/1/reschedule" || path == "/api/schedules/1/cancel" {
            guard input["expected_updated_at"] == schedule["updated_at"] else { return (409, .object(["detail": .string("Schedule changed. Refresh first.")]), [:]) }
            if path.hasSuffix("reschedule") { schedule["scheduled_at"] = input["scheduled_local"] }
            else { schedule["status"] = .string("cancelled") }
            schedule["updated_at"] = .string(ISO8601DateFormatter().string(from: Date()))
            return ok(schedule)
        }
        if path == "/api/series" { return ok(.array([])) }
        if path == "/api/analytics/dashboard" {
            return ok(.object(["summary": .object(["impressions": .integer(1240), "engagements": .integer(84), "comments": .integer(16), "followers": .integer(380), "posts": .integer(6)]), "platforms": .object(["instagram": .object(["connected": .bool(true), "account": .string("Pottery Studio"), "impressions": .integer(1240), "engagements": .integer(84), "followers": .integer(380)])]), "top_posts": .array([]), "recommendations": .array([.object(["title": .string("Show the process"), "detail": .string("Try another simple pottery demonstration.")])]), "note": .string("Synthetic simulator evidence. No real provider data.")]))
        }
        if path.hasPrefix("/api/publications/") { return ok(.object(["draft_status": .string("draft"), "results": .object([:])])) }
        if path == "/api/publish-context" {
            var context = JSONValue.object(["connection_id": .integer(1), "accounts": .array([.object(["id": .integer(1), "name": .string("Pottery Studio")])])])
            if primaryPlatform == "tiktok" {
                context["posting_mode"] = .string("direct")
                context["privacy_options"] = .strings(["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"])
                context["private_test_mode"] = .bool(false)
            }
            return ok(.object(["platforms": .object([primaryPlatform: context])]))
        }
        if path == "/api/publish-review" {
            var snapshot = input
            snapshot["targets"] = .object(["instagram": .object(["display_name": .string("Pottery Studio"), "username": .string("pottery"), "format": .string("post"), "posts": input["variants"]["instagram"]["posts"]])]); snapshot["media"] = .array([])
            return ok(.object(["review_token": .string("synthetic-review-only"), "snapshot": snapshot]))
        }
        return (400, .object(["detail": .string("This offline fixture does not implement " + path)]), [:])
    }
}
#endif
