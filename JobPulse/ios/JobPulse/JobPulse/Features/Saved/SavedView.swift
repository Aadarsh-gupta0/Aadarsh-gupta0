import SwiftUI

/// Jobs you kept, split by whether you have applied yet.
struct SavedView: View {
    @Environment(SavedStore.self) private var saved
    @Environment(AppRouter.self) private var router

    @State private var scope: SaveState = .saved

    var body: some View {
        @Bindable var router = self.router

        NavigationStack(path: $router.savedPath) {
            ZStack {
                AuroraBackground()

                ScrollView {
                    VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                        Text("Saved")
                            .font(.system(size: 32, weight: .bold))
                            .foregroundStyle(Theme.Palette.textPrimary)
                            .padding(.top, Theme.Spacing.s)

                        scopePicker

                        LoadableContent(
                            state: saved.state,
                            isEmpty: filtered.isEmpty,
                            emptyTitle: scope == .saved ? "Nothing saved yet" : "No applications yet",
                            emptyMessage: scope == .saved
                                ? "Swipe a card right, or tap the star, to keep it here."
                                : "Roles you open with Apply are tracked here.",
                            onRetry: { Task { await saved.load() } }
                        ) {
                            list
                        }
                    }
                    .padding(.horizontal, Theme.Spacing.l)
                    .padding(.bottom, Theme.Spacing.tabBarClearance)
                }
                .scrollIndicators(.hidden)
                .refreshable { await saved.load() }
            }
            .navigationBarHidden(true)
            .navigationDestination(for: JobRoute.self) { route in
                switch route {
                case .detail(let id): JobDetailView(jobId: id)
                case .company(let slug): CompanyView(slug: slug)
                }
            }
        }
        .task { await saved.load() }
    }

    private var scopePicker: some View {
        HStack(spacing: Theme.Spacing.s) {
            ForEach([SaveState.saved, .applied], id: \.self) { option in
                let isSelected = scope == option
                Button {
                    withAnimation(Theme.Motion.interactive) { scope = option }
                    Haptics.play(.selection)
                } label: {
                    HStack(spacing: 5) {
                        Image(systemName: option.symbolName)
                            .font(.system(size: 11, weight: .semibold))
                        Text(option.label)
                            .font(.system(size: 14, weight: .semibold))
                        Text("\(count(for: option))")
                            .font(Theme.Typeface.micro)
                            .foregroundStyle(Theme.Palette.textTertiary)
                    }
                    .foregroundStyle(
                        isSelected ? Theme.Palette.textPrimary : Theme.Palette.textSecondary
                    )
                    .padding(.horizontal, 16)
                    .padding(.vertical, 9)
                    .background {
                        Capsule()
                            .fill(
                                isSelected
                                    ? Theme.Palette.accent.opacity(0.85)
                                    : Color.white.opacity(0.08)
                            )
                    }
                    .contentShape(Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(isSelected ? [.isSelected, .isButton] : .isButton)
            }
            Spacer()
        }
    }

    private var filtered: [SavedJob] {
        saved.items.filter { $0.state == scope }
    }

    private func count(for state: SaveState) -> Int {
        saved.items.filter { $0.state == state }.count
    }

    private var list: some View {
        LazyVStack(spacing: Theme.Spacing.m) {
            ForEach(filtered) { item in
                VStack(alignment: .leading, spacing: 0) {
                    JobNotificationCard(
                        job: item.job,
                        isSaved: true,
                        showsSaveButton: false
                    )
                    .onTapGesture { router.savedPath.append(JobRoute.detail(item.job.id)) }

                    if let note = item.note, !note.isEmpty {
                        Text(note)
                            .font(Theme.Typeface.micro)
                            .foregroundStyle(Theme.Palette.textTertiary)
                            .padding(.top, 6)
                            .padding(.leading, Theme.Spacing.xs)
                    }
                }
                .contextMenu {
                    Button {
                        Task { await saved.set(item.job, to: item.state == .applied ? .saved : .applied) }
                    } label: {
                        Label(
                            item.state == .applied ? "Mark as saved" : "Mark as applied",
                            systemImage: item.state == .applied ? "bookmark" : "paperplane"
                        )
                    }
                    Button(role: .destructive) {
                        Task { await saved.remove(item.job) }
                    } label: {
                        Label("Remove", systemImage: "trash")
                    }
                }
            }
        }
        .animation(Theme.Motion.gentle, value: filtered.map(\.id))
    }
}

#Preview {
    SavedView()
        .environment(SavedStore())
        .environment(AppRouter())
        .preferredColorScheme(.dark)
}
