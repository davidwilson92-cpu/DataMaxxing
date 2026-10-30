import XCTest
@testable import Zova

final class ProductContractTests: XCTestCase {
    func testFacebookAvailabilityRequiresCustomerApprovalOrAnExistingPage() {
        var account: JSONValue = .object(["connection_options": .object(["facebook": .object(["available": .bool(true)])])])
        XCTAssertFalse(ProductConnections.canConnect("facebook", account: account))
        for platform in ["instagram", "x", "tiktok"] {
            XCTAssertTrue(ProductConnections.canConnect(platform, account: account))
        }
        account["connections"] = .array([.object(["platform": .string("instagram")])])
        XCTAssertFalse(ProductConnections.canConnect("facebook", account: account))
        account["connections"] = .array([.object(["platform": .string("facebook"), "status": .string("reconnect")])])
        XCTAssertTrue(ProductConnections.canConnect("facebook", account: account))
        account["connections"] = .array([])
        account["connection_options"] = .object(["facebook": .object(["customer_access": .bool(true)])])
        XCTAssertTrue(ProductConnections.canConnect("facebook", account: account))
    }
    func testDeletionReceiptOnlyAcceptsTheExactOwnedOpaqueStatusPath() throws {
        let configuration = try ZovaConfiguration(base: URL(string: "https://zova-social.com")!)
        let path = "/data-deletion/status/" + String(repeating: "a", count: 64)
        XCTAssertEqual(ProductLinks.deletionReceipt(path, configuration: configuration)?.absoluteString, "https://zova-social.com" + path)
        for invalid in ["", "/account", path + "?next=https://example.com", path + "#other", path + "/", String(path.dropLast()), "https://zova-social.com" + path, "//example.com" + path, "/data-deletion/status/../account", "/data-deletion/status/" + String(repeating: "z", count: 64)] {
            XCTAssertNil(ProductLinks.deletionReceipt(invalid, configuration: configuration))
        }
    }
    func testScheduleOffsetsAndNaiveServerUTCRemainDistinctFromLocalTimes() throws {
        let utc = try XCTUnwrap(ProductLinks.date("2026-10-27T17:30:00Z"))
        XCTAssertEqual(ProductLinks.date("2026-10-27T12:30:00-05:00"), utc)
        XCTAssertEqual(ProductLinks.date("2026-10-27T17:30:00"), utc)
        XCTAssertEqual(ProductLinks.localDate("2026-10-27T12:30", timezone: "America/New_York"), utc.addingTimeInterval(-3600))
        XCTAssertNil(ProductLinks.date("not a date"))
    }
    func testDraftPreservesConversationAttachmentsAndUnknownWorkspaceFields() throws {
        let source = Data("""
        {"id":24,"revision":7,"status":"draft","brief":"A real idea","thread_length":3,
        "variants":{"instagram":{"posts":["Caption"]}},"workspace":{"composer":"Unsent text",
        "selected_platforms":["instagram"],"media":[{"id":4,"kind":"video"}],
        "media_asset_ids":[4],"future_field":{"keep":true},"conversation":[{"role":"user","content":"Sent idea","media_asset_ids":[4]}]}}
        """.utf8)
        var draft = ProductDraft(try JSONDecoder().decode(JSONValue.self, from: source))
        XCTAssertEqual(draft.id, 24); XCTAssertEqual(draft.revision, 7)
        XCTAssertEqual(draft.composer, "Unsent text")
        draft.composer = "Another thought"
        let roundTrip = try JSONDecoder().decode(JSONValue.self, from: draft.payload.encoded())
        XCTAssertEqual(roundTrip["workspace"]["conversation"].array.first?["media_asset_ids"], .array([.integer(4)]))
        XCTAssertTrue(roundTrip["workspace"]["future_field"]["keep"].bool)
        XCTAssertEqual(roundTrip["workspace"]["composer"].string, "Another thought")
        XCTAssertEqual(roundTrip["thread_length"].int, 3)
    }
    func testUndoKeepsOnlyThreeCaptionStatesAndDoesNotLoseMedia() {
        var draft = ProductDraft()
        draft.workspace["media_asset_ids"] = .array([.integer(9)])
        for index in 0..<5 { draft.variants = .object(["instagram": .object(["posts": .strings([String(index)])])]); draft.addHistory() }
        XCTAssertEqual(draft.workspace["text_history"].array.count, 3)
        draft.addHistory()
        XCTAssertEqual(draft.workspace["text_history"].array.count, 3, "Focusing unchanged text must not consume undo history")
        draft.undo()
        XCTAssertEqual(draft.variants["instagram"]["posts"].strings, ["3"])
        XCTAssertEqual(draft.workspace["media_asset_ids"], .array([.integer(9)]))
    }
    func testMissingMetricsRemainNullAndUnsafeExternalLinksAreRejected() throws {
        let data = try JSONDecoder().decode(JSONValue.self, from: Data("{\"missing\":null,\"zero\":0,\"allowed\":false}".utf8))
        XCTAssertTrue(data["missing"].isNull); XCTAssertFalse(data["zero"].isNull)
        XCTAssertFalse(data["allowed"].bool)
        for text in ["javascript:alert(1)", "file:///tmp/private", "https://user:password@example.com/", "//example.com", "http://example.com"] { XCTAssertNil(ProductLinks.external(text)) }
        XCTAssertNotNil(ProductLinks.external("https://www.instagram.com/p/example"))
    }
    func testSubmittedDraftDoesNotBecomeEditableFromClientMetadata() throws {
        for status in ["published", "scheduled", "pending", "publishing", "needs_review"] {
            let draft = ProductDraft(.object(["status": .string(status)]))
            XCTAssertFalse(draft.editable)
        }
    }
}
