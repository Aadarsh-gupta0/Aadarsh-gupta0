import SwiftUI

/// Placeholder rows shown while the first page loads.
struct SkeletonFeed: View {
    var rows = 4

    @State private var shimmer = false

    var body: some View {
        VStack(spacing: Theme.Spacing.m) {
            ForEach(0..<rows, id: \.self) { index in
                HStack(spacing: Theme.Spacing.m) {
                    RoundedRectangle(cornerRadius: 11, style: .continuous)
                        .frame(width: 38, height: 38)
                    VStack(alignment: .leading, spacing: 7) {
                        RoundedRectangle(cornerRadius: 4).frame(width: 96, height: 11)
                        RoundedRectangle(cornerRadius: 4).frame(height: 9)
                        RoundedRectangle(cornerRadius: 4).frame(width: 140, height: 9)
                    }
                    Spacer()
                }
                .foregroundStyle(Color.white.opacity(0.10))
                .padding(Theme.Spacing.m)
                .glassPanel()
                .opacity(shimmer ? 0.55 : 1)
                .animation(
                    .easeInOut(duration: 1.1)
                        .repeatForever(autoreverses: true)
                        .delay(Double(index) * 0.12),
                    value: shimmer
                )
            }
        }
        .onAppear { shimmer = true }
        .accessibilityLabel("Loading jobs")
    }
}

/// Shared empty / error presentation.
struct StatusCard: View {
    var symbolName: String
    var title: String
    var message: String
    var actionTitle: String?
    var action: (() -> Void)?

    var body: some View {
        VStack(spacing: Theme.Spacing.m) {
            Image(systemName: symbolName)
                .font(.system(size: 30, weight: .light))
                .foregroundStyle(Theme.Palette.textSecondary)
                .padding(.bottom, 2)

            Text(title)
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(Theme.Palette.textPrimary)

            Text(message)
                .font(Theme.Typeface.cardBody)
                .foregroundStyle(Theme.Palette.textSecondary)
                .multilineTextAlignment(.center)
                .fixedSize(horizontal: false, vertical: true)

            if let actionTitle, let action {
                Button(action: action) {
                    Text(actionTitle)
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(Theme.Palette.textPrimary)
                        .padding(.horizontal, 22)
                        .padding(.vertical, 10)
                }
                .buttonStyle(GlassButtonStyle(tint: Theme.Palette.accent))
                .padding(.top, 4)
            }
        }
        .frame(maxWidth: .infinity)
        .padding(Theme.Spacing.xl)
        .glassPanel()
    }
}

/// Wraps a screen body and swaps in the right state view.
struct LoadableContent<Content: View>: View {
    let state: LoadState
    let isEmpty: Bool
    var emptyTitle: String = "Nothing here yet"
    var emptyMessage: String = "New roles land here as soon as they are posted."
    var onRetry: () -> Void
    @ViewBuilder var content: Content

    var body: some View {
        switch state {
        case .loading where isEmpty:
            SkeletonFeed()
        case .failed(let message):
            StatusCard(
                symbolName: "antenna.radiowaves.left.and.right.slash",
                title: "Could not reach the server",
                message: message,
                actionTitle: "Try again",
                action: onRetry
            )
        case .idle, .loading, .loaded:
            if isEmpty, state == .loaded {
                StatusCard(
                    symbolName: "tray",
                    title: emptyTitle,
                    message: emptyMessage,
                    actionTitle: "Refresh",
                    action: onRetry
                )
            } else {
                content
            }
        }
    }
}
