import SwiftUI

/// Serialise edits from this screen. The server revision also protects other devices.
@MainActor
final class CampaignBriefWriter: ObservableObject {
    private(set) var revision = 0
    private var pending: JSONValue = .null
    private var saved: JSONValue = .null
    private var writing: Task<Void, Error>?
    @Published private(set) var note = ""

    func restore(_ value: JSONValue, revision: Int, restored: Bool) {
        self.revision = revision
        saved = value; pending = value
        note = restored ? "Brief restored" : ""
    }

    func save(_ value: JSONValue, store: ProductStore) async throws {
        pending = value
        if let writing { try await writing.value; return }
        guard pending != saved else { return }
        let authority = store.authority
        let task = Task { @MainActor in
            defer { writing = nil }
            do {
                while pending != saved {
                    guard authority == store.authority else { throw CancellationError() }
                    let snapshot = pending
                    var body = snapshot; body["revision"] = .integer(revision)
                    note = "Saving brief…"
                    let reply = try await store.request("/api/campaign-brief", method: "POST", body: body)
                    revision = reply["revision"].int; saved = snapshot
                }
                note = "Brief saved"
            } catch {
                note = "Brief not saved. " + error.localizedDescription
                throw error
            }
        }
        writing = task
        try await task.value
    }
}
