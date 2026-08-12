import SwiftUI

/// Search reached from the circular button beside the tab bar.
struct SearchSheet: View {
    @Environment(JobStore.self) private var jobs
    @Environment(PreferencesStore.self) private var preferences
    @Environment(SavedStore.self) private var saved
    @Environment(\.dismiss) private var dismiss

    @FocusState private var fieldFocused: Bool
    var onSelect: (Job) -> Void

    var body: some View {
        @Bindable var jobs = self.jobs

        ZStack {
            AuroraBackground()

            VStack(spacing: Theme.Spacing.m) {
                HStack(spacing: Theme.Spacing.s) {
                    Image(systemName: "magnifyingglass")
                        .foregroundStyle(Theme.Palette.textTertiary)

                    TextField("Role, company or skill", text: $jobs.searchQuery)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .focused($fieldFocused)
                        .foregroundStyle(Theme.Palette.textPrimary)
                        .submitLabel(.search)

                    if !jobs.searchQuery.isEmpty {
                        Button {
                            jobs.searchQuery = ""
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundStyle(Theme.Palette.textTertiary)
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel("Clear search")
                    }
                }
                .padding(Theme.Spacing.m)
                .glassPanel(cornerRadius: Theme.Radius.small)

                if jobs.searchQuery.isEmpty {
                    suggestions
                } else {
                    results
                }

                Spacer(minLength: 0)
            }
            .padding(Theme.Spacing.l)
        }
        .presentationDetents([.large])
        .presentationBackground(.clear)
        .onAppear { fieldFocused = true }
        .onChange(of: jobs.searchQuery) { _, _ in
            jobs.searchChanged(interests: preferences.selectedInterests)
        }
        .onDisappear {
            // Leave the feed unfiltered when the sheet closes.
            if !jobs.searchQuery.isEmpty {
                jobs.searchQuery = ""
                jobs.searchChanged(interests: preferences.selectedInterests)
            }
        }
    }

    private var suggestions: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            Text("Try")
                .font(Theme.Typeface.micro)
                .foregroundStyle(Theme.Palette.textTertiary)

            FlowLayout(spacing: 8) {
                ForEach(Self.suggestionTerms, id: \.self) { term in
                    Button {
                        jobs.searchQuery = term
                    } label: {
                        Text(term)
                            .font(Theme.Typeface.caption)
                            .foregroundStyle(Theme.Palette.textPrimary)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 7)
                    }
                    .buttonStyle(GlassButtonStyle())
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var results: some View {
        ScrollView {
            LazyVStack(spacing: Theme.Spacing.m) {
                if jobs.jobs.isEmpty, jobs.feedState == .loaded {
                    StatusCard(
                        symbolName: "magnifyingglass",
                        title: "No results",
                        message: "Nothing matched “\(jobs.searchQuery)”.",
                        actionTitle: nil,
                        action: nil
                    )
                }
                ForEach(jobs.jobs) { job in
                    JobNotificationCard(
                        job: job,
                        isSaved: saved.isSaved(job),
                        onSave: { Task { await saved.toggleSave(job) } }
                    )
                    .onTapGesture {
                        onSelect(job)
                        dismiss()
                    }
                }
            }
        }
        .scrollIndicators(.hidden)
    }

    private static let suggestionTerms = [
        "Flutter", "Internship", "Figma", "Product Designer", "Remote", "Dart", "UX Research"
    ]
}
