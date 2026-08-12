import Foundation
import Observation
import UserNotifications
#if canImport(UIKit)
import UIKit
#endif

/// Owns the notification permission flow and the APNs token handoff.
@MainActor
@Observable
final class PushManager: NSObject {
    enum Authorization: Equatable {
        case unknown
        case notDetermined
        case authorized
        case provisional
        case denied

        var allowsAlerts: Bool { self == .authorized || self == .provisional }
    }

    private(set) var authorization: Authorization = .unknown
    private(set) var lastError: String?

    /// Injected by the app so the manager can forward the token and deep links.
    var onTokenReceived: ((String) -> Void)?
    var onJobOpened: ((Int) -> Void)?

    private let center = UNUserNotificationCenter.current()

    func bootstrap() async {
        center.delegate = self
        await refreshAuthorization()
        if authorization.allowsAlerts {
            registerWithAPNs()
        }
    }

    func refreshAuthorization() async {
        let settings = await center.notificationSettings()
        authorization =
            switch settings.authorizationStatus {
            case .notDetermined: .notDetermined
            case .denied: .denied
            case .authorized: .authorized
            case .provisional: .provisional
            case .ephemeral: .provisional
            @unknown default: .unknown
            }
    }

    /// Asks for permission. `provisional` is requested alongside so a user who
    /// declines the prompt still gets quiet alerts in Notification Centre.
    @discardableResult
    func requestAuthorization() async -> Bool {
        do {
            let granted = try await center.requestAuthorization(
                options: [.alert, .sound, .badge, .provisional]
            )
            await refreshAuthorization()
            if granted { registerWithAPNs() }
            return granted
        } catch {
            lastError = error.localizedDescription
            return false
        }
    }

    func registerWithAPNs() {
        #if canImport(UIKit) && !targetEnvironment(simulator)
        UIApplication.shared.registerForRemoteNotifications()
        #elseif canImport(UIKit)
        // The simulator issues tokens only on macOS 13+/Xcode 14+ with a signed
        // build; calling this there is harmless and keeps the flow identical.
        UIApplication.shared.registerForRemoteNotifications()
        #endif
    }

    func didRegister(deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        onTokenReceived?(token)
    }

    func didFailToRegister(error: Error) {
        lastError = error.localizedDescription
    }

    func clearBadge() {
        center.setBadgeCount(0) { _ in }
    }

    /// Registers the actions shown when a job alert is long-pressed.
    func registerCategories() {
        let save = UNNotificationAction(
            identifier: "SAVE_JOB",
            title: "Save",
            options: []
        )
        let apply = UNNotificationAction(
            identifier: "APPLY_JOB",
            title: "Apply",
            options: [.foreground]
        )
        let category = UNNotificationCategory(
            identifier: "JOB_ALERT",
            actions: [save, apply],
            intentIdentifiers: [],
            options: []
        )
        center.setNotificationCategories([category])
    }
}

extension PushManager: UNUserNotificationCenterDelegate {
    /// Show the banner even when the app is open — a job alert is worth
    /// interrupting a scroll for, and it matches the lock-screen presentation.
    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        [.banner, .sound, .list, .badge]
    }

    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let userInfo = response.notification.request.content.userInfo
        guard let jobId = userInfo["jobId"] as? Int else { return }

        await MainActor.run {
            switch response.actionIdentifier {
            case "APPLY_JOB":
                if let raw = userInfo["applyUrl"] as? String, let url = URL(string: raw) {
                    #if canImport(UIKit)
                    UIApplication.shared.open(url)
                    #endif
                } else {
                    onJobOpened?(jobId)
                }
            default:
                onJobOpened?(jobId)
            }
        }
    }
}
