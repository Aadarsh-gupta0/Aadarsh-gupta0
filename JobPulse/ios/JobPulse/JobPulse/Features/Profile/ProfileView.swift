import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

/// Interests, alert sensitivity and notification permission.
struct ProfileView: View {
    @Environment(PreferencesStore.self) private var preferences
    @Environment(PushManager.self) private var push

    @FocusState private var nameFieldFocused: Bool

    var body: some View {
        NavigationStack {
            ZStack {
                AuroraBackground()

                ScrollView {
                    VStack(alignment: .leading, spacing: Theme.Spacing.l) {
                        Text("You")
                            .font(.system(size: 32, weight: .bold))
                            .foregroundStyle(Theme.Palette.textPrimary)
                            .padding(.top, Theme.Spacing.s)

                        nameCard
                        notificationCard
                        interestsCard
                        sensitivityCard
                        deliveryCard
                        aboutCard
                    }
                    .padding(.horizontal, Theme.Spacing.l)
                    .padding(.bottom, Theme.Spacing.tabBarClearance)
                }
                .scrollIndicators(.hidden)
                .scrollDismissesKeyboard(.interactively)
            }
            .navigationBarHidden(true)
        }
        .task {
            await preferences.loadCatalogue()
            await push.refreshAuthorization()
        }
    }

    // MARK: Name

    @ViewBuilder
    private var nameCard: some View {
        @Bindable var preferences = self.preferences

        DetailSection(title: "Greeting") {
            VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                TextField("Your name", text: $preferences.settings.displayName)
                    .textInputAutocapitalization(.words)
                    .autocorrectionDisabled()
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(Theme.Palette.textPrimary)
                    .focused($nameFieldFocused)
                    .submitLabel(.done)
                    .onSubmit { nameFieldFocused = false }

                Text("Shown on the home screen as “\(preferences.greeting)”.")
                    .font(Theme.Typeface.micro)
                    .foregroundStyle(Theme.Palette.textTertiary)
            }
        }
    }

    // MARK: Notifications

    @ViewBuilder
    private var notificationCard: some View {
        @Bindable var preferences = self.preferences

        DetailSection(title: "Notifications") {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                switch push.authorization {
                case .authorized, .provisional:
                    Toggle(isOn: $preferences.settings.pushEnabled) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Push alerts").foregroundStyle(Theme.Palette.textPrimary)
                            Text("Grouped by company, like the lock screen")
                                .font(Theme.Typeface.micro)
                                .foregroundStyle(Theme.Palette.textTertiary)
                        }
                    }
                    .tint(Theme.Palette.accent)

                case .denied:
                    permissionRow(
                        message: "Notifications are turned off for JobPulse in Settings.",
                        actionTitle: "Open Settings"
                    ) {
                        #if canImport(UIKit)
                        if let url = URL(string: UIApplication.openSettingsURLString) {
                            UIApplication.shared.open(url)
                        }
                        #endif
                    }

                default:
                    permissionRow(
                        message: "Allow notifications to get roles the moment they are posted.",
                        actionTitle: "Allow"
                    ) {
                        Task { await push.requestAuthorization() }
                    }
                }

                if preferences.registration == nil, preferences.settings.pushEnabled {
                    Text(
                        preferences.registrationError
                            ?? "Waiting for a device token from Apple…"
                    )
                    .font(Theme.Typeface.micro)
                    .foregroundStyle(Theme.Palette.warning)
                }
            }
            .font(Theme.Typeface.cardBody)
        }
    }

    private func permissionRow(
        message: String,
        actionTitle: String,
        action: @escaping () -> Void
    ) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            Text(message)
                .font(Theme.Typeface.cardBody)
                .foregroundStyle(Theme.Palette.textSecondary)
                .fixedSize(horizontal: false, vertical: true)

            Button(action: action) {
                Text(actionTitle)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(Theme.Palette.textPrimary)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 9)
            }
            .buttonStyle(GlassButtonStyle(tint: Theme.Palette.accent))
        }
    }

    // MARK: Interests

    private var interestsCard: some View {
        DetailSection(title: "Interests") {
            VStack(spacing: Theme.Spacing.s) {
                ForEach(preferences.catalogue) { interest in
                    InterestRow(
                        interest: interest,
                        isSelected: preferences.isSelected(interest.slug),
                        onToggle: { preferences.toggle(interest.slug) }
                    )
                }
            }
        }
    }

    // MARK: Sensitivity

    @ViewBuilder
    private var sensitivityCard: some View {
        @Bindable var preferences = self.preferences

        DetailSection(title: "Alert sensitivity") {
            VStack(alignment: .leading, spacing: Theme.Spacing.m) {
                HStack {
                    Text(sensitivityLabel)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(Theme.Palette.textPrimary)
                    Spacer()
                    Text("\(Int(preferences.settings.minScore * 100))% match")
                        .font(Theme.Typeface.numeric)
                        .foregroundStyle(Theme.Palette.textSecondary)
                }

                Slider(value: $preferences.settings.minScore, in: 0.3...0.95, step: 0.05)
                    .tint(Theme.Palette.accent)

                Text(
                    "Only roles scoring above this are pushed. Everything above 35% still shows in the feed."
                )
                .font(Theme.Typeface.micro)
                .foregroundStyle(Theme.Palette.textTertiary)
                .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var sensitivityLabel: String {
        switch preferences.settings.minScore {
        case ..<0.45: "Everything relevant"
        case ..<0.65: "Balanced"
        case ..<0.8: "Strong matches only"
        default: "Near-perfect matches only"
        }
    }

    // MARK: Delivery

    @ViewBuilder
    private var deliveryCard: some View {
        @Bindable var preferences = self.preferences

        DetailSection(title: "Delivery") {
            VStack(spacing: Theme.Spacing.m) {
                Toggle(isOn: $preferences.settings.internshipsOnly) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Internships only").foregroundStyle(Theme.Palette.textPrimary)
                        Text("Filters out full-time roles")
                            .font(Theme.Typeface.micro)
                            .foregroundStyle(Theme.Palette.textTertiary)
                    }
                }
                .tint(Theme.Palette.accent)

                Toggle(isOn: $preferences.settings.quietHoursEnabled) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Quiet hours").foregroundStyle(Theme.Palette.textPrimary)
                        Text("Holds alerts between 22:00 and 07:00")
                            .font(Theme.Typeface.micro)
                            .foregroundStyle(Theme.Palette.textTertiary)
                    }
                }
                .tint(Theme.Palette.accent)
            }
            .font(Theme.Typeface.cardBody)
        }
    }

    // MARK: About

    private var aboutCard: some View {
        DetailSection(title: "About") {
            VStack(alignment: .leading, spacing: Theme.Spacing.s) {
                LabeledContent("Version", value: APIConfig.appVersion)
                LabeledContent("Server", value: APIConfig.baseURL.absoluteString)
                LabeledContent(
                    "Device",
                    value: preferences.registration.map { "#\($0.id)" } ?? "Not registered"
                )
            }
            .font(Theme.Typeface.micro)
            .foregroundStyle(Theme.Palette.textSecondary)
        }
    }
}

// MARK: - Interest row

struct InterestRow: View {
    let interest: Interest
    let isSelected: Bool
    let onToggle: () -> Void

    var body: some View {
        Button(action: onToggle) {
            HStack(spacing: Theme.Spacing.m) {
                Image(systemName: interest.symbolName)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(interest.color)
                    .frame(width: 34, height: 34)
                    .background(Circle().fill(interest.color.opacity(0.18)))

                VStack(alignment: .leading, spacing: 2) {
                    Text(interest.label)
                        .font(.system(size: 15, weight: .semibold))
                        .foregroundStyle(Theme.Palette.textPrimary)
                    Text(interest.tagline)
                        .font(Theme.Typeface.micro)
                        .foregroundStyle(Theme.Palette.textTertiary)
                        .lineLimit(2)
                        .multilineTextAlignment(.leading)
                }

                Spacer(minLength: Theme.Spacing.s)

                Image(systemName: isSelected ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 20))
                    .foregroundStyle(isSelected ? interest.color : Theme.Palette.textTertiary)
                    .contentTransition(.symbolEffect(.replace))
            }
            .padding(.vertical, 6)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(interest.label)
        .accessibilityValue(isSelected ? "On" : "Off")
        .accessibilityAddTraits(.isButton)
    }
}

#Preview {
    ProfileView()
        .environment(PreferencesStore())
        .environment(PushManager())
        .preferredColorScheme(.dark)
}
