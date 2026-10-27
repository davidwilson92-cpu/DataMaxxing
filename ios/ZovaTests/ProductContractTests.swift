import XCTest
@testable import Zova

final class ProductContractTests: XCTestCase {
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
        draft.undo()
        XCTAssertEqual(draft.variants["instagram"]["posts"].strings, ["4"])
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
