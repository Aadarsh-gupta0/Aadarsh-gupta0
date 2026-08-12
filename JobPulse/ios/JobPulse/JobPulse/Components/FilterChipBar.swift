import SwiftUI

/// The All / Popular / New row from the reference design.
///
/// The selected pill is one shared shape moved with `matchedGeometryEffect`
/// rather than a fill toggled per chip, so selection slides instead of blinking.
struct FilterChipBar: View {
    @Binding var selection: FeedFilter
    var filters: [FeedFilter] = FeedFilter.allCases

    @Namespace private var namespace

    var body: some View {
        ScrollView(.horizontal) {
            HStack(spacing: Theme.Spacing.s) {
                ForEach(filters) { filter in
                    chip(for: filter)
                }
            }
            .padding(.horizontal, Theme.Spacing.l)
            .padding(.vertical, 2)
        }
        .scrollIndicators(.hidden)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Filter jobs")
    }

    private func chip(for filter: FeedFilter) -> some View {
        let isSelected = selection == filter

        return Button {
            withAnimation(Theme.Motion.interactive) { selection = filter }
        } label: {
            Text(filter.label)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(
                    isSelected ? Theme.Palette.textPrimary : Theme.Palette.textSecondary
                )
                .padding(.horizontal, 18)
                .padding(.vertical, 9)
                .background {
                    if isSelected {
                        Capsule()
                            .fill(Theme.Palette.accent)
                            .matchedGeometryEffect(id: "chip", in: namespace)
                            .shadow(color: Theme.Palette.accent.opacity(0.5), radius: 12, y: 4)
                    } else {
                        Capsule()
                            .fill(.ultraThinMaterial)
                            .overlay(Capsule().fill(Color.white.opacity(0.06)))
                            .overlay(
                                Capsule().strokeBorder(Color.white.opacity(0.12), lineWidth: 0.5)
                            )
                    }
                }
                .contentShape(Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityAddTraits(isSelected ? [.isSelected, .isButton] : .isButton)
    }
}

#Preview {
    @Previewable @State var selection: FeedFilter = .all
    ZStack {
        AuroraBackground()
        FilterChipBar(selection: $selection)
    }
}
