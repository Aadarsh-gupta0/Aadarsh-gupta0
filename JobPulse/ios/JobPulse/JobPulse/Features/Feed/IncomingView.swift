import SwiftUI

/// Everything that has come in, grouped by company into collapsible stacks.
///
/// This is the screen that mirrors the lock screen: the same grouping key the
/// server puts in the push payload (`thread-id`) is the key used here, so a
/// company that arrives as one stack of notifications stays one stack in the app.
struct IncomingView: View {
    @Environment(JobStore.self) private var jobs
    @Environment(PreferencesStore.self) private var preferences
    @Environment(SavedStore.self) private var saved
    @Environment(AppRouter.self) private var router

    @State private var expandedCompany: String?
    @State private var clearedCompanies: Set<String> = []

    var body: some View {
        @Bindable var router = self.router

        NavigationStack(path: $router.incomingPath) {
            ZStack {
                AuroraBackground()

                ScrollView {
                    VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                        header

                        LoadableContent(
                            state: jobs.stackState,
                            isEmpty: visibleStacks.isEmpty,
                            emptyTitle: clearedCompanies.isEmpty ? "Inbox zero" : "All caught up",
                            emptyMessage:
                                "New roles matching Flutter, UI/UX and Product Design will stack up here.",
                            onRetry: { Task { await reload(force: true) } }
                        ) {
                            stacksList
                        }
                    }
                    .padding(.horizontal, Theme.Spacing.l)
                    .padding(.bottom, Theme.Spacing.tabBarClearance)
                }
                .scrollIndicators(.hidden)
                .refreshable {
                    // Pulling down also un-clears anything dismissed with the
                    // X button, so the gesture is never a dead end.
                    clearedCompanies.removeAll()
                    await reload(force: true)
                }
            }
            .navigationBarHidden(true)
            .navigationDestination(for: JobRoute.self) { route in
                switch route {
                case .detail(let id): JobDetailView(jobId: id)
                case .company(let slug): CompanyView(slug: slug)
                }
            }
        }
        .task { await reload() }
    }

    // MARK: Header

    private var header: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            HStack(alignment: .firstTextBaseline) {
                Text("Incoming")
                    .font(.system(size: 32, weight: .bold))
                    .foregroundStyle(Theme.Palette.textPrimary)

                Spacer()

                if !visibleStacks.isEmpty {
                    Button {
                        withAnimation(Theme.Motion.stack) {
                            clearedCompanies.formUnion(visibleStacks.map(\.company.slug))
                        }
                        Haptics.play(.soft)
                    } label: {
                        Image(systemName: "xmark")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(Theme.Palette.textSecondary)
                            .frame(width: 30, height: 30)
                            .background(Circle().fill(Color.white.opacity(0.12)))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Clear all")
                }
            }

            Text(summary)
                .font(Theme.Typeface.caption)
                .foregroundStyle(Theme.Palette.textSecondary)
        }
        .padding(.top, Theme.Spacing.s)
    }

    private var summary: String {
        let roles = visibleStacks.reduce(0) { $0 + $1.count }
        guard roles > 0 else { return "Nothing waiting" }
        return "\(roles) roles across \(visibleStacks.count) companies"
    }

    // MARK: Stacks

    private var visibleStacks: [CompanyStack] {
        jobs.stacks.filter { !clearedCompanies.contains($0.company.slug) }
    }

    private var stacksList: some View {
        LazyVStack(alignment: .leading, spacing: Theme.Spacing.xl) {
            ForEach(visibleStacks) { stack in
                NotificationStack(
                    stack: stack,
                    expandedCompany: $expandedCompany,
                    savedIds: saved.savedIds,
                    onSelect: { job in
                        router.incomingPath.append(JobRoute.detail(job.id))
                    },
                    onSave: { job in
                        Task { await saved.toggleSave(job) }
                    },
                    onDismiss: { job in
                        Task { await saved.set(job, to: .dismissed) }
                    }
                )
                .transition(.asymmetric(
                    insertion: .opacity.combined(with: .move(edge: .top)),
                    removal: .opacity.combined(with: .scale(scale: 0.9))
                ))
            }
        }
        .animation(Theme.Motion.stack, value: visibleStacks.map(\.id))
    }

    private func reload(force: Bool = false) async {
        await jobs.loadStacks(interests: preferences.selectedInterests, force: force)
    }
}

#Preview {
    @Previewable @State var expanded: String?
    ZStack {
        AuroraBackground()
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                ForEach(CompanyStack.previewList) { stack in
                    NotificationStack(
                        stack: stack,
                        expandedCompany: $expanded,
                        savedIds: [1],
                        onSelect: { _ in },
                        onSave: { _ in },
                        onDismiss: { _ in }
                    )
                }
            }
            .padding()
        }
    }
}
