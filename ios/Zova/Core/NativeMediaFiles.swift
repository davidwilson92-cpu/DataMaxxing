import Foundation

/// Short-lived files owned exclusively by Zova. Never delete a caller's picker file.
enum NativeMediaFiles {
    static let directory = FileManager.default.temporaryDirectory.appendingPathComponent("ZovaNativeMedia", isDirectory: true)
    static func create(extension ext: String) throws -> URL {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true,
                                               attributes: [.protectionKey: FileProtectionType.complete])
        let suffix = ext.lowercased().filter { $0.isASCII && ($0.isLetter || $0.isNumber) }
        let url = directory.appendingPathComponent(UUID().uuidString + "." + String(suffix.prefix(12)))
        guard FileManager.default.createFile(atPath: url.path, contents: nil, attributes: [.protectionKey: FileProtectionType.complete]) else { throw ZovaFailure.unavailable }
        return url
    }
    static func remove(_ url: URL?) {
        guard let url, url.isFileURL, url.deletingLastPathComponent().standardizedFileURL == directory.standardizedFileURL else { return }
        try? FileManager.default.removeItem(at: url)
    }
    static func clear() {
        guard let files = try? FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil) else { return }
        files.forEach(remove)
    }
    static func multipart(file: URL, filename: String, mime: String, boundary: String) throws -> URL {
        guard file.isFileURL else { throw ZovaFailure.unsafeURL }
        let safeName = filename.replacingOccurrences(of: "\"", with: "").replacingOccurrences(of: "\r", with: "").replacingOccurrences(of: "\n", with: "")
        guard !mime.contains("\r"), !mime.contains("\n") else { throw ZovaFailure.invalidResponse }
        let destination = try create(extension: "multipart")
        do {
            let input = try FileHandle(forReadingFrom: file), output = try FileHandle(forWritingTo: destination)
            defer { try? input.close(); try? output.close() }
            try output.write(contentsOf: Data("--\(boundary)\r\nContent-Disposition: form-data; name=\"files\"; filename=\"\(safeName)\"\r\nContent-Type: \(mime)\r\n\r\n".utf8))
            var size = 0
            while let chunk = try input.read(upToCount: 65_536), !chunk.isEmpty {
                size += chunk.count
                guard size <= 150 * 1024 * 1024 else { throw ZovaFailure.server("Choose a file smaller than 150 MB.") }
                try output.write(contentsOf: chunk)
            }
            guard size > 0 else { throw ZovaFailure.server("This file is empty. Choose another attachment.") }
            try output.write(contentsOf: Data("\r\n--\(boundary)--\r\n".utf8))
            return destination
        } catch { remove(destination); throw error }
    }
}
