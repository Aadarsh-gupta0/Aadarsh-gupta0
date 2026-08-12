import SwiftUI

/// Floating tab bar modelled on the Apple Store app: a frosted capsule of tabs
/// with a separate circular action sitting beside it.
struct GlassTabBar: View {
    @Binding var selection: AppTab
    var unreadCount: Int = 0
    var onSearch: () -> Void

    @Namespace private var namespace

    var body: some View {
        HStack(spacing: Theme.Spacing.m) {
            HStack(spacing: 2) {
                ForEach(AppTab.allCases) { tab in
                    tabButton(tab)
                }
            }
            .padding(6)
            .glassPill(fill: Theme.Glass.fillRaised)

            Button(action: onSearch) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(Theme.Palette.textPrimary)
                    .frame(width: 50, height: 50)
            }
            .buttonStyle(.plain)
            .glassPill(fill: Theme.Glass.fillRaised)
            .accessibilityLabel("Search jobs")
        }
        .padding(.horizontal, Theme.Spacing.l)
        .padding(.bottom, Theme.Spacing.s)
    }

    private func tabButton(_ tab: AppTab) -> some View {
        let isSelected = selection == tab

        return Button {
            withAnimation(Theme.Motion.interactive) { selection = tab }
            Haptics.play(.light)
        } label: {
            VStack(spacing: 3) {
                ZStack {
                    Image(systemName: tab.symbolName)
                        .font(.system(size: 16, weight: isSelected ? .semibold : .medium))
                        // `symbolVariant` degrades to the outline automatically
                        // for any symbol without a filled counterpart.
                        .symbolVariant(isSelected ? .fill : .none)

                    if tab == .incoming, unreadCount > 0 {
                        Text(unreadCount > 9 ? "9+" : "\(unreadCount)")
                            .font(.system(size: 9, weight: .bold))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 4)
                            .padding(.vertical, 1.5)
                            .background(Capsule().fill(Theme.Palette.destructive))
                            .offset(x: 12, y: -9)
                    }
                }
                .frame(height: 20)

                Text(tab.title)
                    .font(.system(size: 10, weight: isSelected ? .semibold : .medium))
                    .lineLimit(1)
            }
            .foregroundStyle(isSelected ? Theme.Palette.textPrimary : Theme.Palette.textTertiary)
            .frame(width: 62, height: 44)
            .background {
                if isSelected {
                    Capsule()
                        .fill(Color.white.opacity(0.14))
                        .matchedGeometryEffect(id: "tab", in: namespace)
                }
            }
            .contentShape(Capsule())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(tab.title)
        .accessibilityAddTraits(isSelected ? [.isSelected, .isButton] : .isButton)
    }
}

#Preview {
    @Previewable @State var tab: AppTab = .home
    ZStack {
        AuroraBackground()
        VStack {
            Spacer()
            GlassTabBar(selection: $tab, unreadCount: 3) {}
        }
    }
}
