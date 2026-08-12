import SwiftUI

/// The screen from the reference design: floating bubbles, a serif greeting,
/// the All / Popular / New chips, and a feed of notification-shaped cards.
struct HomeView: View {
    @Environment(JobStore.self) private var jobs
    @Environment(PreferencesStore.self) private var preferences
    @Environment(SavedStore.self) private var saved
    @Environment(AppRouter.self) private var router

    var body: some View {
        @Bindable var jobs = self.jobs
        @Bindable var router = self.router

        NavigationStack(path: $router.homePath) {
            ZStack {
                AuroraBackground()

                ScrollView {
                    VStack(spacing: Theme.Spacing.l) {
                        GreetingHeader(
                            greeting: preferences.greeting,
                            matchCount: jobs.total,
                            onProfileTap: { router.select(.profile) }
                        )

                        FilterChipBar(selection: $jobs.filter)

                        LoadableContent(
                            state: jobs.feedState,
                            isEmpty: jobs.jobs.isEmpty,
                            emptyTitle: emptyTitle,
                            emptyMessage: emptyMessage,
                            onRetry: { Task { await reload(force: true) } }
                        ) {
                            feed
                        }
                        .padding(.horizontal, Theme.Spacing.l)
                    }
                    .padding(.bottom, Theme.Spacing.tabBarClearance)
                }
                .scrollIndicators(.hidden)
                .refreshable { await reload(force: true) }
            }
            .navigationBarHidden(true)
            .navigationDestination(for: JobRoute.self) { route in
                destination(for: route)
            }
        }
        .task { await reload() }
        .onChange(of: jobs.filter) { _, _ in
            jobs.filterChanged(interests: preferences.selectedInterests)
        }
    }

    // MARK: Feed

    private var feed: some View {
        LazyVStack(spacing: Theme.Spacing.m) {
            ForEach(jobs.jobs) { job in
                JobNotificationCard(
                    job: job,
                    isSaved: saved.isSaved(job),
                    onSave: { Task { await saved.toggleSave(job) } }
                )
                .onTapGesture { router.homePath.append(JobRoute.detail(job.id)) }
                // Cards compress and dim as they approach the edge of the
                // viewport, which is what gives the feed its "pile of cards"
                // silhouette without any fixed stacking maths.
                .scrollTransition(.interactive, axis: .vertical) { content, phase in
                    content
                        .scaleEffect(phase.isIdentity ? 1 : 0.93)
                        .opacity(phase.isIdentity ? 1 : 0.55)
                }
                .task { await jobs.loadMoreIfNeeded(currentItem: job) }
            }

            if jobs.isLoadingMore {
                ProgressView()
                    .tint(Theme.Palette.textSecondary)
                    .padding(.vertical, Theme.Spacing.m)
            }
        }
    }

    @ViewBuilder
    private func destination(for route: JobRoute) -> some View {
        switch route {
        case .detail(let id):
            JobDetailView(jobId: id)
        case .company(let slug):
            CompanyView(slug: slug)
        }
    }

    // MARK: Copy

    private var emptyTitle: String {
        jobs.searchQuery.isEmpty ? "No matches yet" : "Nothing for “\(jobs.searchQuery)”"
    }

    private var emptyMessage: String {
        switch jobs.filter {
        case .new:
            "Nothing posted in the last 48 hours. Try All to see everything matched so far."
        case .internships:
            "No internships matched your interests yet."
        case .remote:
            "No remote roles matched your interests yet."
        default:
            "Run the backend's ingest once, or widen your interests in the You tab."
        }
    }

    private func reload(force: Bool = false) async {
        await preferences.loadCatalogue()
        await jobs.load(interests: preferences.selectedInterests, force: force)
    }
}

// MARK: - Header

struct GreetingHeader: View {
    let greeting: String
    let matchCount: Int
    var onProfileTap: () -> Void

    var body: some View {
        ZStack(alignment: .top) {
            BubbleField()
                .frame(height: 190)

            VStack(spacing: Theme.Spacing.s) {
                HStack {
                    Spacer()
                    Button(action: onProfileTap) {
                        ZStack(alignment: .topTrailing) {
                            Circle()
                                .fill(.ultraThinMaterial)
                                .overlay(Circle().fill(Theme.Palette.accent.opacity(0.25)))
                                .overlay(
                                    Circle().strokeBorder(
                                        Color.white.opacity(0.25),
                                        lineWidth: 0.5
                                    )
                                )
                                .frame(width: 38, height: 38)
                                .overlay {
                                    Image(systemName: "person.fill")
                                        .font(.system(size: 15, weight: .medium))
                                        .foregroundStyle(Theme.Palette.textPrimary)
                                }

                            if matchCount > 0 {
                                Circle()
                                    .fill(Theme.Palette.destructive)
                                    .frame(width: 10, height: 10)
                                    .overlay(Circle().strokeBorder(Theme.Palette.canvas, lineWidth: 1.5))
                                    .offset(x: 2, y: -2)
                            }
                        }
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Your profile and interests")
                }
                .padding(.horizontal, Theme.Spacing.l)

                Spacer(minLength: Theme.Spacing.l)

                Text(greeting)
                    .font(Theme.Typeface.greeting())
                    .foregroundStyle(Theme.Palette.textPrimary)
                    .multilineTextAlignment(.center)
                    .shadow(color: .black.opacity(0.35), radius: 12, y: 4)

                Text(subtitle)
                    .font(Theme.Typeface.caption)
                    .foregroundStyle(Theme.Palette.textSecondary)
            }
            .frame(height: 190)
        }
        .accessibilityElement(children: .contain)
    }

    private var subtitle: String {
        matchCount == 0
            ? "Matching roles to your interests"
            : "\(matchCount) roles matched to you"
    }
}

#Preview {
    ZStack {
        AuroraBackground()
        ScrollView {
            VStack(spacing: Theme.Spacing.l) {
                GreetingHeader(greeting: "Hi Aadarsh", matchCount: 24, onProfileTap: {})
                FilterChipBar(selection: .constant(.all))
                LazyVStack(spacing: Theme.Spacing.m) {
                    ForEach(Job.previewList) { job in
                        JobNotificationCard(job: job, isSaved: job.id == 1, onSave: {})
                    }
                }
                .padding(.horizontal, Theme.Spacing.l)
            }
        }
    }
}
