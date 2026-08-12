import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

@main
struct JobPulseApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    @State private var preferences = PreferencesStore()
    @State private var jobs = JobStore()
    @State private var saved = SavedStore()
    @State private var router = AppRouter()
    @State private var push = PushManager()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(preferences)
                .environment(jobs)
                .environment(saved)
                .environment(router)
                .environment(push)
                .task { await bootstrap() }
        }
    }

    @MainActor
    private func bootstrap() async {
        appDelegate.push = push

        push.registerCategories()
        push.onTokenReceived = { token in
            Task { @MainActor in
                await preferences.updateAPNsToken(token)
                saved.configure(token: token)
                await saved.load()
            }
        }
        push.onJobOpened = { jobId in
            router.openJob(id: jobId)
        }

        saved.configure(token: preferences.apnsToken)
        await push.bootstrap()
        await preferences.loadCatalogue()
    }
}

/// Only exists for the two APNs callbacks SwiftUI has no equivalent for.
final class AppDelegate: NSObject, UIApplicationDelegate {
    /// Set by the app once the scene's state objects exist.
    var push: PushManager?

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        Task { @MainActor in push?.didRegister(deviceToken: deviceToken) }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        Task { @MainActor in push?.didFailToRegister(error: error) }
    }
}
