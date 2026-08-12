import SwiftUI

/// Tab container. A plain `ZStack` rather than `TabView` because the floating
/// glass bar has to sit over the content, and each tab keeps its own
/// `NavigationStack` so deep links land in the right place.
struct RootView: View {
    @Environment(PreferencesStore.self) private var preferences
    @Environment(JobStore.self) private var jobs
    @Environment(SavedStore.self) private var saved
    @Environment(AppRouter.self) private var router
    @Environment(PushManager.self) private var push
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        @Bindable var router = self.router

        ZStack {
            Theme.Palette.canvas.ignoresSafeArea()

            if preferences.hasOnboarded {
                mainInterface
            } else {
                OnboardingView()
                    .transition(.opacity)
            }
        }
        .preferredColorScheme(.dark)
        .animation(Theme.Motion.gentle, value: preferences.hasOnboarded)
        .sheet(isPresented: $router.isSearching) {
            SearchSheet { job in
                router.openJob(id: job.id)
            }
        }
        // One place to persist and sync every setting. `@Observable` has no
        // `didSet`, so this replaces per-property observers.
        .onChange(of: preferences.settings) { _, _ in
            preferences.settingsChanged()
        }
        .onChange(of: preferences.selectedInterests) { _, interests in
            Task { await jobs.refreshAll(interests: interests) }
        }
        .onChange(of: scenePhase) { _, phase in
            guard phase == .active else { return }
            push.clearBadge()
            Task {
                await push.refreshAuthorization()
                await jobs.refreshAll(interests: preferences.selectedInterests)
            }
        }
        .onOpenURL { url in router.handle(url: url) }
    }

    private var mainInterface: some View {
        ZStack(alignment: .bottom) {
            // All four stay alive so scroll position and stack expansion
            // survive tab switches. Hit testing has to be disabled on the
            // hidden ones or they swallow taps meant for the visible tab.
            HomeView().tabVisible(router.selectedTab == .home)
            IncomingView().tabVisible(router.selectedTab == .incoming)
            SavedView().tabVisible(router.selectedTab == .saved)
            ProfileView().tabVisible(router.selectedTab == .profile)

            GlassTabBar(
                selection: Binding(
                    get: { router.selectedTab },
                    set: { router.select($0) }
                ),
                unreadCount: unreadCount,
                onSearch: { router.isSearching = true }
            )
        }
    }

    /// Roles posted in the last 48 hours that have not been saved or dismissed.
    private var unreadCount: Int {
        let handled = saved.savedIds.union(saved.dismissedIds)
        return jobs.stacks
            .flatMap(\.jobs)
            .filter { $0.isNew && !handled.contains($0.id) }
            .count
    }
}

private extension View {
    /// Keeps an off-screen tab mounted but fully inert.
    func tabVisible(_ visible: Bool) -> some View {
        self
            .opacity(visible ? 1 : 0)
            .allowsHitTesting(visible)
            .accessibilityHidden(!visible)
            .zIndex(visible ? 1 : 0)
    }
}

#Preview {
    RootView()
        .environment(PreferencesStore())
        .environment(JobStore())
        .environment(SavedStore())
        .environment(AppRouter())
        .environment(PushManager())
}
