import UserNotifications

/// Turns the plain alert APNs delivers into a rich one.
///
/// The server sets `mutable-content: 1` and includes `logoUrl`; this extension
/// downloads that image and attaches it, so the banner shows the company's mark
/// instead of the app icon. It also appends the match percentage to the
/// subtitle, which is the fastest signal for deciding whether to open the alert.
///
/// Apple gives the extension roughly 30 seconds. Every failure path here falls
/// back to delivering the original content rather than dropping the alert.
final class NotificationService: UNNotificationServiceExtension {

    private var contentHandler: ((UNNotificationContent) -> Void)?
    private var bestAttempt: UNMutableNotificationContent?
    private var downloadTask: URLSessionDownloadTask?

    override func didReceive(
        _ request: UNNotificationRequest,
        withContentHandler contentHandler: @escaping (UNNotificationContent) -> Void
    ) {
        self.contentHandler = contentHandler
        guard
            let mutable = request.content.mutableCopy() as? UNMutableNotificationContent
        else {
            contentHandler(request.content)
            return
        }
        bestAttempt = mutable

        let info = request.content.userInfo
        decorate(mutable, with: info)

        guard
            let raw = info["logoUrl"] as? String,
            let url = URL(string: raw)
        else {
            contentHandler(mutable)
            return
        }

        downloadTask = URLSession.shared.downloadTask(with: url) { [weak self] location, response, _ in
            guard let self else { return }
            defer { self.deliver() }

            guard
                let location,
                let response,
                let attachment = Self.makeAttachment(from: location, response: response)
            else { return }

            self.bestAttempt?.attachments = [attachment]
        }
        downloadTask?.resume()
    }

    /// Fired when the extension runs out of time — deliver what we have.
    override func serviceExtensionTimeWillExpire() {
        downloadTask?.cancel()
        deliver()
    }

    // MARK: - Content

    private func decorate(_ content: UNMutableNotificationContent, with info: [AnyHashable: Any]) {
        var suffixes: [String] = []

        if let score = info["score"] as? Double {
            suffixes.append("\(Int((score * 100).rounded()))% match")
        }
        if info["isInternship"] as? Bool == true {
            suffixes.append("Internship")
        } else if info["isRemote"] as? Bool == true {
            suffixes.append("Remote")
        }

        if !suffixes.isEmpty {
            let joined = suffixes.joined(separator: " · ")
            content.subtitle =
                content.subtitle.isEmpty ? joined : "\(content.subtitle) — \(joined)"
        }

        // Keeps the grouped summary line readable when several land at once.
        if let company = info["companyName"] as? String {
            content.summaryArgument = company
        }
    }

    private func deliver() {
        guard let contentHandler, let bestAttempt else { return }
        self.contentHandler = nil
        contentHandler(bestAttempt)
    }

    // MARK: - Attachment

    /// Attachments must live at a stable path with a correct extension, so the
    /// download is copied out of the temporary location first.
    private static func makeAttachment(
        from location: URL,
        response: URLResponse
    ) -> UNNotificationAttachment? {
        let suggested = response.suggestedFilename ?? location.lastPathComponent
        var name = (suggested as NSString).lastPathComponent
        if (name as NSString).pathExtension.isEmpty {
            name += Self.fileExtension(for: response.mimeType)
        }

        let directory = URL(fileURLWithPath: NSTemporaryDirectory())
            .appendingPathComponent(ProcessInfo.processInfo.globallyUniqueString, isDirectory: true)

        do {
            try FileManager.default.createDirectory(
                at: directory,
                withIntermediateDirectories: true
            )
            let destination = directory.appendingPathComponent(name)
            try FileManager.default.moveItem(at: location, to: destination)
            return try UNNotificationAttachment(identifier: "logo", url: destination)
        } catch {
            return nil
        }
    }

    private static func fileExtension(for mimeType: String?) -> String {
        switch mimeType {
        case "image/png": ".png"
        case "image/jpeg": ".jpg"
        case "image/gif": ".gif"
        case "image/webp": ".webp"
        default: ".png"
        }
    }
}
