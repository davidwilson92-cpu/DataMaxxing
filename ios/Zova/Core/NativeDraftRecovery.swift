import Foundation
import CryptoKit

enum NativeDraftRecovery {
    private static let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appendingPathComponent("DraftRecovery", isDirectory: true)
    private static func location(_ owner: String) -> URL {
        let namespace = ZovaConfiguration.bundled.base.absoluteString + ":" + owner
        let hash = SHA256.hash(data: Data(namespace.utf8)).map { String(format: "%02x", $0) }.joined()
        return directory.appendingPathComponent(hash + ".json")
    }
    static func save(_ draft: ProductDraft, owner: String) throws {
        guard draft.editable else { return }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.protectionKey: FileProtectionType.complete])
        var excluded = directory; var resources = URLResourceValues(); resources.isExcludedFromBackup = true; try excluded.setResourceValues(resources)
        var value = draft.payload
        value["id"] = draft.id.map { .integer($0) } ?? .null
        value["status"] = .string(draft.status); value["display_title"] = .string(draft.title)
        let data = try value.encoded()
        guard data.count <= 4 * 1024 * 1024 else { throw ZovaFailure.invalidResponse }
        try data.write(to: location(owner), options: [.atomic, .completeFileProtection])
    }
    static func load(owner: String) -> JSONValue {
        guard let data = try? Data(contentsOf: location(owner)), data.count <= 4 * 1024 * 1024 else { return .null }
        return (try? JSONDecoder().decode(JSONValue.self, from: data)) ?? .null
    }
    static func remove(owner: String) { try? FileManager.default.removeItem(at: location(owner)) }
}
