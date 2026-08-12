import SwiftUI

/// Full posting: company blurb, stats, links, description and related roles —
/// the second screen from the paper sketches.
struct JobDetailView: View {
    let jobId: Int

    @Environment(JobStore.self) private var jobs
    @Environment(SavedStore.self) private var saved
    @Environment(\.dismiss) private var dismiss
    @Environment(\.openURL) private var openURL

    @State private var job: Job?
    @State private var isLoading = true

    var body: some View {
        ZStack {
            AuroraBackground(tint: job?.accentColor)

            if let job {
                content(for: job)
            } else if isLoading {
                ProgressView().tint(Theme.Palette.textSecondary)
            } else {
                StatusCard(
                    symbolName: "questionmark.folder",
                    title: "Job not found",
                    message: "It may have been taken down since the alert was sent.",
                    actionTitle: "Go back",
                    action: { dismiss() }
                )
                .padding(Theme.Spacing.l)
            }
        }
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task { await load() }
    }

    private func content(for job: Job) -> some View {
        ZStack(alignment: .bottom) {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                    hero(job)
                    if let detail = job.companyDetail {
                        companySection(detail)
                        statsSection(detail)
                        linksSection(detail)
                    }
                    descriptionSection(job)
                    relatedSection(job)
                }
                .padding(.horizontal, Theme.Spacing.l)
                .padding(.bottom, 120)
            }
            .scrollIndicators(.hidden)

            actionBar(job)
        }
    }

    // MARK: Hero

    private func hero(_ job: Job) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.m) {
            HStack(spacing: Theme.Spacing.m) {
                CompanyAvatar(company: job.company, size: 54, accent: job.accentColor)

                VStack(alignment: .leading, spacing: 3) {
                    Text(job.company.name)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(Theme.Palette.textSecondary)
                    Text(job.postedRelative + " · via " + job.source)
                        .font(Theme.Typeface.micro)
                        .foregroundStyle(Theme.Palette.textTertiary)
                }
                Spacer()
            }

            Text(job.title)
                .font(.system(size: 28, weight: .bold))
                .foregroundStyle(Theme.Palette.textPrimary)
                .fixedSize(horizontal: false, vertical: true)

            if !job.attributes.isEmpty {
                FlowLayout(spacing: 6) {
                    ForEach(job.attributes, id: \.self) { attribute in
                        AttributePill(text: attribute)
                    }
                }
            }

            if !job.matches.isEmpty {
                VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                    Text("Why you're seeing this")
                        .font(Theme.Typeface.micro)
                        .foregroundStyle(Theme.Palette.textTertiary)

                    ForEach(job.matches) { match in
                        HStack(spacing: Theme.Spacing.s) {
                            MatchBadge(match: match)
                            Text(match.matchedTerms.prefix(4).joined(separator: " · "))
                                .font(Theme.Typeface.micro)
                                .foregroundStyle(Theme.Palette.textSecondary)
                                .lineLimit(1)
                        }
                    }
                }
                .padding(Theme.Spacing.m)
                .frame(maxWidth: .infinity, alignment: .leading)
                .glassPanel(cornerRadius: Theme.Radius.small)
            }
        }
        .padding(.top, Theme.Spacing.s)
    }

    // MARK: Sections

    private func companySection(_ detail: CompanyDetail) -> some View {
        Group {
            if let description = detail.description, !description.isEmpty {
                DetailSection(title: "About \(detail.name)") {
                    Text(description)
                        .font(Theme.Typeface.cardBody)
                        .foregroundStyle(Theme.Palette.textSecondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
    }

    private func statsSection(_ detail: CompanyDetail) -> some View {
        DetailSection(title: "Stats") {
            LazyVGrid(
                columns: [GridItem(.flexible()), GridItem(.flexible())],
                spacing: Theme.Spacing.m
            ) {
                ForEach(detail.stats) { stat in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(stat.label)
                            .font(Theme.Typeface.micro)
                            .foregroundStyle(Theme.Palette.textTertiary)
                        Text(stat.value)
                            .font(.system(size: 15, weight: .semibold))
                            .foregroundStyle(Theme.Palette.textPrimary)
                            .lineLimit(1)
                            .minimumScaleFactor(0.7)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
    }

    private func linksSection(_ detail: CompanyDetail) -> some View {
        Group {
            if !detail.links.isEmpty {
                DetailSection(title: "Links") {
                    VStack(spacing: 0) {
                        ForEach(Array(detail.links.enumerated()), id: \.element.id) {
                            index, link in
                            Button {
                                openURL(link.url)
                            } label: {
                                HStack {
                                    Text(link.label)
                                        .font(Theme.Typeface.cardBody)
                                        .foregroundStyle(Theme.Palette.textPrimary)
                                    Spacer()
                                    Image(systemName: "arrow.up.right")
                                        .font(.system(size: 12, weight: .semibold))
                                        .foregroundStyle(Theme.Palette.textTertiary)
                                }
                                .padding(.vertical, 12)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)

                            if index < detail.links.count - 1 {
                                Divider().overlay(Color.white.opacity(0.10))
                            }
                        }
                    }
                }
            }
        }
    }

    private func descriptionSection(_ job: Job) -> some View {
        Group {
            if let text = job.descriptionText, !text.isEmpty {
                DetailSection(title: "Job description") {
                    Text(text)
                        .font(Theme.Typeface.cardBody)
                        .foregroundStyle(Theme.Palette.textSecondary)
                        .lineSpacing(3)
                        .fixedSize(horizontal: false, vertical: true)
                        .textSelection(.enabled)
                }
            }
        }
    }

    private func relatedSection(_ job: Job) -> some View {
        Group {
            if let related = job.related, !related.isEmpty {
                VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                    Text("More at \(job.company.name)")
                        .font(Theme.Typeface.sectionTitle)
                        .foregroundStyle(Theme.Palette.textPrimary)

                    ForEach(related) { other in
                        NavigationLink(value: JobRoute.detail(other.id)) {
                            JobNotificationCard(job: other, showsSaveButton: false)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
    }

    // MARK: Actions

    private func actionBar(_ job: Job) -> some View {
        HStack(spacing: Theme.Spacing.m) {
            Button {
                Task { await saved.toggleSave(job) }
            } label: {
                Image(systemName: saved.isSaved(job) ? "bookmark.fill" : "bookmark")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(
                        saved.isSaved(job) ? Theme.Palette.warning : Theme.Palette.textPrimary
                    )
                    .frame(width: 54, height: 52)
                    .contentTransition(.symbolEffect(.replace))
            }
            .buttonStyle(GlassButtonStyle(cornerRadius: Theme.Radius.small))
            .accessibilityLabel(saved.isSaved(job) ? "Remove from saved" : "Save job")

            Button {
                guard let url = job.applyURL else { return }
                Task { await saved.set(job, to: .applied) }
                openURL(url)
            } label: {
                Label("Apply", systemImage: "arrow.up.right")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Theme.Palette.textPrimary)
                    .frame(maxWidth: .infinity)
                    .frame(height: 52)
            }
            .buttonStyle(GlassButtonStyle(cornerRadius: Theme.Radius.small, tint: job.accentColor))
            .disabled(job.applyURL == nil)
        }
        .padding(.horizontal, Theme.Spacing.l)
        .padding(.bottom, Theme.Spacing.m)
        .background {
            LinearGradient(
                colors: [.clear, Theme.Palette.canvas.opacity(0.92)],
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
            .allowsHitTesting(false)
        }
    }

    private func load() async {
        job = jobs.detail(for: jobId)
        isLoading = job == nil
        job = await jobs.loadDetail(id: jobId) ?? job
        isLoading = false
    }
}

// MARK: - Section shell

struct DetailSection<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            Text(title)
                .font(Theme.Typeface.sectionTitle)
                .foregroundStyle(Theme.Palette.textPrimary)

            content
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(Theme.Spacing.m)
                .glassPanel()
        }
    }
}

#Preview {
    NavigationStack {
        JobDetailView(jobId: 1)
            .environment(JobStore())
            .environment(SavedStore())
    }
    .preferredColorScheme(.dark)
}
