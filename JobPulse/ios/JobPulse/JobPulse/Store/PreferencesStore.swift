import Foundation
import Observation

/// Everything the user can change, in one Equatable value.
///
/// Grouping the settings means a single `onChange` in `RootView` can persist
/// and sync them. That matters because `@Observable` does not support `didSet`
/// on tracked properties — a per-property observer would either fail to compile
/// or silently stop publishing changes to SwiftUI.
struct UserSettings: Codable, Equatable, Sendable {
    var displayName: String = ""
    var interests: [String] = ["flutter", "ui_ux", "product_design"]
    var pushEnabled: Bool = true
    var internshipsOnly: Bool = false
    /// Alert threshold: a job must score at least this to be pushed.
    var minScore: Double = 0.55
    var quietHoursEnabled: Bool = true
}

@MainActor
@Observable
final class PreferencesStore {
    private enum Key {
        static let settings = "jobpulse.settings"
        static let installId = "jobpulse.installId"
        static let apnsToken = "jobpulse.apnsToken"
        static let onboarded = "jobpulse.onboarded"
    }

    // MARK: Observable state

    var settings: UserSettings
    private(set) var catalogue: [Interest] = []
    private(set) var hasOnboarded: Bool
    private(set) var apnsToken: String?
    private(set) var registration: DeviceProfile?
    private(set) var registrationError: String?

    let installId: String

    @ObservationIgnored private let defaults: UserDefaults
    @ObservationIgnored private let api: APIClient
    @ObservationIgnored private var syncTask: Task<Void, Never>?

    init(defaults: UserDefaults = .standard, api: APIClient = .shared) {
        self.defaults = defaults
        self.api = api

        if let data = defaults.data(forKey: Key.settings),
           let decoded = try? JSONDecoder().decode(UserSettings.self, from: data) {
            settings = decoded
        } else {
            settings = UserSettings()
        }

        hasOnboarded = defaults.bool(forKey: Key.onboarded)
        apnsToken = defaults.string(forKey: Key.apnsToken)

        if let existing = defaults.string(forKey: Key.installId) {
            installId = existing
        } else {
            installId = UUID().uuidString
            defaults.set(installId, forKey: Key.installId)
        }
    }

    // MARK: Derived

    /// "Hi Aadarsh" in the reference design.
    var greeting: String {
        let trimmed = settings.displayName.trimmingCharacters(in: .whitespaces)
        return trimmed.isEmpty ? "Hi there" : "Hi \(trimmed)"
    }

    var selectedInterests: [String] { settings.interests }

    var activeInterests: [Interest] {
        catalogue.filter { settings.interests.contains($0.slug) }
    }

    func isSelected(_ slug: String) -> Bool { settings.interests.contains(slug) }

    func toggle(_ slug: String) {
        if let index = settings.interests.firstIndex(of: slug) {
            // Never let the user end up with an empty feed.
            guard settings.interests.count > 1 else { return }
            settings.interests.remove(at: index)
        } else {
            settings.interests.append(slug)
        }
        Haptics.play(.selection)
    }

    func completeOnboarding() {
        hasOnboarded = true
        defaults.set(true, forKey: Key.onboarded)
    }

    // MARK: Catalogue

    func loadCatalogue() async {
        guard catalogue.isEmpty else { return }
        do {
            catalogue = try await api.interests()
        } catch {
            catalogue = Interest.fallbackCatalogue
        }
    }

    // MARK: Persistence + sync

    /// Called from `RootView` whenever `settings` changes. Writes to disk
    /// immediately and coalesces a burst of toggles into one PATCH.
    func settingsChanged() {
        persist()
        guard apnsToken != nil else { return }

        syncTask?.cancel()
        syncTask = Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(600))
            guard !Task.isCancelled else { return }
            await self?.syncNow()
        }
    }

    private func persist() {
        guard let data = try? JSONEncoder().encode(settings) else { return }
        defaults.set(data, forKey: Key.settings)
    }

    // MARK: Registration

    func updateAPNsToken(_ token: String) async {
        apnsToken = token
        defaults.set(token, forKey: Key.apnsToken)
        await register()
    }

    func register() async {
        guard let apnsToken else { return }
        do {
            registration = try await api.register(
                DeviceRegistration(
                    apnsToken: apnsToken,
                    installId: installId,
                    displayName: settings.displayName.isEmpty ? nil : settings.displayName,
                    interests: settings.interests,
                    pushEnabled: settings.pushEnabled,
                    internshipsOnly: settings.internshipsOnly,
                    minScore: settings.minScore,
                    quietHoursEnabled: settings.quietHoursEnabled,
                    appVersion: APIConfig.appVersion,
                    environment: Self.apnsEnvironment
                )
            )
            registrationError = nil
        } catch {
            registrationError = Self.message(for: error)
        }
    }

    func syncNow() async {
        guard let apnsToken else { return }
        do {
            registration = try await api.updateDevice(
                token: apnsToken,
                patch: DevicePatch(
                    displayName: settings.displayName.isEmpty ? nil : settings.displayName,
                    interests: settings.interests,
                    pushEnabled: settings.pushEnabled,
                    internshipsOnly: settings.internshipsOnly,
                    minScore: settings.minScore,
                    timezone: TimeZone.current.identifier,
                    quietHoursEnabled: settings.quietHoursEnabled,
                    appVersion: APIConfig.appVersion
                )
            )
            registrationError = nil
        } catch APIError.http(status: 404, _) {
            // The server forgot us (fresh database) — re-register instead.
            await register()
        } catch {
            registrationError = Self.message(for: error)
        }
    }

    private static func message(for error: Error) -> String {
        (error as? APIError)?.errorDescription ?? error.localizedDescription
    }

    private static var apnsEnvironment: String {
        #if DEBUG
        "sandbox"
        #else
        "production"
        #endif
    }
}

extension Interest {
    /// Used when the catalogue endpoint cannot be reached, so onboarding is
    /// never a dead end.
    static let fallbackCatalogue: [Interest] = [
        Interest(
            slug: "flutter",
            label: "Flutter Dev",
            tagline: "Flutter, Dart and cross-platform mobile",
            accent: "#43D9AD"
        ),
        Interest(
            slug: "ui_ux",
            label: "UI / UX",
            tagline: "Interface, interaction and experience design",
            accent: "#7C8CFF"
        ),
        Interest(
            slug: "product_design",
            label: "Product Design",
            tagline: "End-to-end product thinking and craft",
            accent: "#FF7C9C"
        ),
        Interest(
            slug: "govt_research",
            label: "Govt & Research",
            tagline: "DRDO, ISRO, national labs and research internships",
            accent: "#F5C451"
        )
    ]
}
