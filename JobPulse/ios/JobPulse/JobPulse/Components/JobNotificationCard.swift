import SwiftUI

/// A job rendered the way iOS renders a notification: icon, source name, body.
///
/// Keeping the feed card and the push banner visually identical is the point of
/// the app — what lands on the lock screen is what you scroll through later.
struct JobNotificationCard: View {
    enum Style {
        /// Fixed height, used inside a collapsed stack.
        case compact
        /// Grows to fit, adds match badge and attribute pills.
        case full
    }

    let job: Job
    var style: Style = .full
    var isSaved = false
    var showsSaveButton = true
    var onSave: (() -> Void)?

    var body: some View {
        HStack(alignment: .top, spacing: Theme.Spacing.m) {
            CompanyAvatar(company: job.company, accent: job.accentColor)

            VStack(alignment: .leading, spacing: 5) {
                header
                title
                if style == .full { footer }
            }

            Spacer(minLength: 0)
        }
        .padding(Theme.Spacing.m)
        .frame(maxWidth: .infinity, alignment: .leading)
        .frame(height: style == .compact ? NotificationStack.Metrics.cardHeight : nil)
        .glassPanel(fill: Theme.Glass.fill)
        .accentBloom(job.accentColor, opacity: style == .full ? 0.16 : 0.10)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(accessibilityText)
    }

    private var header: some View {
        HStack(spacing: 6) {
            Text(job.company.name)
                .font(Theme.Typeface.cardTitle)
                .foregroundStyle(Theme.Palette.textPrimary)
                .lineLimit(1)

            if job.isNew {
                Circle()
                    .fill(Theme.Palette.accent)
                    .frame(width: 6, height: 6)
                    .accessibilityHidden(true)
            }

            Spacer(minLength: 4)

            Text(job.postedRelative)
                .font(Theme.Typeface.micro)
                .foregroundStyle(Theme.Palette.textTertiary)

            if showsSaveButton, let onSave {
                Button {
                    onSave()
                } label: {
                    Image(systemName: isSaved ? "star.fill" : "star")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(
                            isSaved ? Theme.Palette.warning : Theme.Palette.textTertiary
                        )
                        .contentTransition(.symbolEffect(.replace))
                }
                .buttonStyle(.plain)
                .accessibilityLabel(isSaved ? "Remove from saved" : "Save job")
            }
        }
    }

    private var title: some View {
        Text(job.title)
            .font(Theme.Typeface.cardBody)
            .foregroundStyle(Theme.Palette.textSecondary)
            .lineLimit(style == .compact ? 2 : 3)
            .multilineTextAlignment(.leading)
            .fixedSize(horizontal: false, vertical: true)
    }

    @ViewBuilder
    private var footer: some View {
        if !job.attributes.isEmpty || job.primaryMatch != nil {
            HStack(spacing: 6) {
                if let match = job.primaryMatch {
                    MatchBadge(match: match)
                }
                ForEach(job.attributes.prefix(2), id: \.self) { attribute in
                    AttributePill(text: attribute)
                }
            }
            .padding(.top, 2)
        }
    }

    private var accessibilityText: String {
        var parts = [job.company.name, job.title]
        parts.append(contentsOf: job.attributes)
        if let match = job.primaryMatch {
            parts.append("Matches \(match.label) at \(match.percentText)")
        }
        parts.append(job.postedRelative)
        return parts.joined(separator: ", ")
    }
}

#Preview {
    ZStack {
        AuroraBackground()
        VStack(spacing: 14) {
            JobNotificationCard(job: .preview, isSaved: true, onSave: {})
            JobNotificationCard(job: .previewInternship, style: .compact, onSave: {})
        }
        .padding()
    }
}
