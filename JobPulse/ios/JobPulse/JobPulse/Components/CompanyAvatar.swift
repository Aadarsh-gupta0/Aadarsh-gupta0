import SwiftUI

/// Company mark, shaped like an app icon so job cards read as notifications.
struct CompanyAvatar: View {
    let company: CompanyBrief
    var size: CGFloat = 38
    var accent: Color = Theme.Palette.accent

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.28, style: .continuous)
                .fill(.ultraThinMaterial)
                .overlay {
                    RoundedRectangle(cornerRadius: size * 0.28, style: .continuous)
                        .fill(accent.opacity(0.22))
                }
                .overlay {
                    RoundedRectangle(cornerRadius: size * 0.28, style: .continuous)
                        .strokeBorder(Color.white.opacity(0.18), lineWidth: 0.5)
                }

            if let logoUrl = company.logoUrl, let url = URL(string: logoUrl) {
                AsyncImage(url: url, transaction: Transaction(animation: .easeIn(duration: 0.2))) {
                    phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(contentMode: .fit)
                            .padding(size * 0.16)
                    case .failure, .empty:
                        monogram
                    @unknown default:
                        monogram
                    }
                }
            } else {
                monogram
            }
        }
        .frame(width: size, height: size)
        .accessibilityHidden(true)
    }

    private var monogram: some View {
        Text(company.monogram)
            .font(.system(size: size * 0.38, weight: .bold, design: .rounded))
            .foregroundStyle(Theme.Palette.textPrimary)
            .minimumScaleFactor(0.6)
            .padding(2)
    }
}

/// Small coloured dot + label showing which interest matched.
struct MatchBadge: View {
    let match: InterestMatch
    var compact = false

    var body: some View {
        HStack(spacing: 5) {
            Circle()
                .fill(match.color)
                .frame(width: 6, height: 6)
                .shadow(color: match.color.opacity(0.8), radius: 4)

            Text(compact ? match.percentText : "\(match.label) · \(match.percentText)")
                .font(Theme.Typeface.micro)
                .foregroundStyle(Theme.Palette.textSecondary)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background {
            Capsule().fill(match.color.opacity(0.14))
        }
        .overlay {
            Capsule().strokeBorder(match.color.opacity(0.28), lineWidth: 0.5)
        }
        .accessibilityLabel("Matches \(match.label), \(match.percentText)")
    }
}

/// Neutral pill for facts like location, salary or employment type.
struct AttributePill: View {
    let text: String
    var symbolName: String?

    var body: some View {
        HStack(spacing: 4) {
            if let symbolName {
                Image(systemName: symbolName).font(.system(size: 9, weight: .semibold))
            }
            Text(text)
                .font(Theme.Typeface.micro)
                .lineLimit(1)
        }
        .foregroundStyle(Theme.Palette.textSecondary)
        .padding(.horizontal, 9)
        .padding(.vertical, 5)
        .background { Capsule().fill(Color.white.opacity(0.08)) }
        .overlay { Capsule().strokeBorder(Color.white.opacity(0.10), lineWidth: 0.5) }
    }
}
