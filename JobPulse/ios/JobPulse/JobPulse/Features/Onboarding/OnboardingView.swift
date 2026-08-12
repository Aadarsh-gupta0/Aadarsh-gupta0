import SwiftUI

/// Three steps: who you are, what you want, and permission to interrupt you.
struct OnboardingView: View {
    @Environment(PreferencesStore.self) private var preferences
    @Environment(PushManager.self) private var push

    @State private var step = 0
    @FocusState private var nameFocused: Bool

    private let lastStep = 2

    var body: some View {
        ZStack {
            AuroraBackground()
            BubbleField()

            VStack(spacing: Theme.Spacing.xl) {
                Spacer(minLength: Theme.Spacing.xxl)

                progressDots

                Group {
                    switch step {
                    case 0: nameStep
                    case 1: interestStep
                    default: notificationStep
                    }
                }
                .transition(.asymmetric(
                    insertion: .opacity.combined(with: .offset(x: 40)),
                    removal: .opacity.combined(with: .offset(x: -40))
                ))

                Spacer()

                primaryButton
            }
            .padding(.horizontal, Theme.Spacing.l)
            .padding(.bottom, Theme.Spacing.xl)
        }
        .task { await preferences.loadCatalogue() }
    }

    // MARK: Steps

    @ViewBuilder
    private var nameStep: some View {
        @Bindable var preferences = self.preferences

        VStack(spacing: Theme.Spacing.l) {
            Text("Hi there")
                .font(Theme.Typeface.greeting(46))
                .foregroundStyle(Theme.Palette.textPrimary)

            Text("What should we call you?")
                .font(Theme.Typeface.cardBody)
                .foregroundStyle(Theme.Palette.textSecondary)

            TextField("Your name", text: $preferences.settings.displayName)
                .textInputAutocapitalization(.words)
                .autocorrectionDisabled()
                .multilineTextAlignment(.center)
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(Theme.Palette.textPrimary)
                .focused($nameFocused)
                .submitLabel(.next)
                .onSubmit { advance() }
                .padding(Theme.Spacing.m)
                .glassPanel()
                .padding(.horizontal, Theme.Spacing.l)
        }
    }

    private var interestStep: some View {
        VStack(spacing: Theme.Spacing.m) {
            Text("What are you looking for?")
                .font(.system(size: 26, weight: .bold))
                .foregroundStyle(Theme.Palette.textPrimary)
                .multilineTextAlignment(.center)

            Text("Alerts are scored against these. You can change them any time.")
                .font(Theme.Typeface.caption)
                .foregroundStyle(Theme.Palette.textSecondary)
                .multilineTextAlignment(.center)
                .padding(.bottom, Theme.Spacing.s)

            ScrollView {
                VStack(spacing: Theme.Spacing.s) {
                    ForEach(preferences.catalogue) { interest in
                        InterestRow(
                            interest: interest,
                            isSelected: preferences.isSelected(interest.slug),
                            onToggle: { preferences.toggle(interest.slug) }
                        )
                        .padding(.horizontal, Theme.Spacing.m)
                        .padding(.vertical, 2)
                        .glassPanel(cornerRadius: Theme.Radius.small)
                    }
                }
            }
            .scrollIndicators(.hidden)
            .frame(maxHeight: 380)
        }
    }

    private var notificationStep: some View {
        VStack(spacing: Theme.Spacing.l) {
            Image(systemName: "bell.badge.fill")
                .font(.system(size: 44))
                .foregroundStyle(Theme.Palette.accent)
                .symbolRenderingMode(.hierarchical)

            Text("Get roles the moment\nthey are posted")
                .font(.system(size: 26, weight: .bold))
                .foregroundStyle(Theme.Palette.textPrimary)
                .multilineTextAlignment(.center)

            Text(
                "Alerts arrive grouped by company, so five roles at one employer stay one stack on your lock screen — not five buzzes."
            )
            .font(Theme.Typeface.cardBody)
            .foregroundStyle(Theme.Palette.textSecondary)
            .multilineTextAlignment(.center)
            .fixedSize(horizontal: false, vertical: true)
            .padding(.horizontal, Theme.Spacing.m)

            if push.authorization == .denied {
                Text("You can turn these on later in Settings.")
                    .font(Theme.Typeface.micro)
                    .foregroundStyle(Theme.Palette.warning)
            }
        }
    }

    // MARK: Chrome

    private var progressDots: some View {
        HStack(spacing: 6) {
            ForEach(0...lastStep, id: \.self) { index in
                Capsule()
                    .fill(
                        index == step
                            ? Theme.Palette.textPrimary
                            : Theme.Palette.textPrimary.opacity(0.25)
                    )
                    .frame(width: index == step ? 20 : 6, height: 6)
            }
        }
        .animation(Theme.Motion.interactive, value: step)
    }

    private var primaryButton: some View {
        Button {
            advance()
        } label: {
            Text(buttonTitle)
                .font(.system(size: 16, weight: .semibold))
                .foregroundStyle(Theme.Palette.textPrimary)
                .frame(maxWidth: .infinity)
                .frame(height: 52)
        }
        .buttonStyle(GlassButtonStyle(cornerRadius: Theme.Radius.small, tint: Theme.Palette.accent))
        .disabled(step == 1 && preferences.selectedInterests.isEmpty)
    }

    private var buttonTitle: String {
        switch step {
        case 0: preferences.settings.displayName.isEmpty ? "Skip" : "Continue"
        case 1: "Continue"
        default: push.authorization == .denied ? "Finish" : "Turn on alerts"
        }
    }

    private func advance() {
        nameFocused = false
        Haptics.play(.light)

        guard step < lastStep else {
            Task {
                if push.authorization != .denied {
                    await push.requestAuthorization()
                }
                preferences.completeOnboarding()
            }
            return
        }
        withAnimation(Theme.Motion.interactive) { step += 1 }
    }
}

#Preview {
    OnboardingView()
        .environment(PreferencesStore())
        .environment(PushManager())
        .preferredColorScheme(.dark)
}
