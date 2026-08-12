import SwiftUI

/// Company profile reached from a job's detail screen.
struct CompanyView: View {
    let slug: String

    @Environment(\.openURL) private var openURL
    @State private var company: CompanyDetail?
    @State private var state: LoadState = .loading

    var body: some View {
        ZStack {
            AuroraBackground()

            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                    if let company {
                        header(company)

                        if let description = company.description, !description.isEmpty {
                            DetailSection(title: "About") {
                                Text(description)
                                    .font(Theme.Typeface.cardBody)
                                    .foregroundStyle(Theme.Palette.textSecondary)
                                    .fixedSize(horizontal: false, vertical: true)
                            }
                        }

                        DetailSection(title: "Stats") {
                            VStack(spacing: Theme.Spacing.s) {
                                ForEach(company.stats) { stat in
                                    HStack {
                                        Text(stat.label)
                                            .font(Theme.Typeface.cardBody)
                                            .foregroundStyle(Theme.Palette.textSecondary)
                                        Spacer()
                                        Text(stat.value)
                                            .font(.system(size: 14, weight: .semibold))
                                            .foregroundStyle(Theme.Palette.textPrimary)
                                    }
                                }
                            }
                        }

                        if !company.links.isEmpty {
                            DetailSection(title: "Links") {
                                VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                                    ForEach(company.links) { link in
                                        Button { openURL(link.url) } label: {
                                            HStack {
                                                Text(link.label)
                                                    .foregroundStyle(Theme.Palette.textPrimary)
                                                Spacer()
                                                Image(systemName: "arrow.up.right")
                                                    .foregroundStyle(Theme.Palette.textTertiary)
                                            }
                                            .font(Theme.Typeface.cardBody)
                                            .contentShape(Rectangle())
                                        }
                                        .buttonStyle(.plain)
                                    }
                                }
                            }
                        }
                    } else if case .failed(let message) = state {
                        StatusCard(
                            symbolName: "building.2",
                            title: "Company unavailable",
                            message: message,
                            actionTitle: "Retry",
                            action: { Task { await load() } }
                        )
                    } else {
                        ProgressView().tint(Theme.Palette.textSecondary)
                            .frame(maxWidth: .infinity)
                            .padding(.top, Theme.Spacing.xxl)
                    }
                }
                .padding(Theme.Spacing.l)
            }
            .scrollIndicators(.hidden)
        }
        .navigationTitle(company?.name ?? "Company")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func header(_ company: CompanyDetail) -> some View {
        HStack(spacing: Theme.Spacing.m) {
            CompanyAvatar(
                company: CompanyBrief(
                    slug: company.slug,
                    name: company.name,
                    logoUrl: company.logoUrl
                ),
                size: 62
            )
            VStack(alignment: .leading, spacing: 4) {
                Text(company.name)
                    .font(.system(size: 24, weight: .bold))
                    .foregroundStyle(Theme.Palette.textPrimary)
                Text("\(company.openRoles) open roles matched to you")
                    .font(Theme.Typeface.caption)
                    .foregroundStyle(Theme.Palette.textSecondary)
            }
            Spacer()
        }
    }

    private func load() async {
        state = .loading
        do {
            company = try await APIClient.shared.company(slug: slug)
            state = .loaded
        } catch {
            state = .failed((error as? APIError)?.errorDescription ?? error.localizedDescription)
        }
    }
}
