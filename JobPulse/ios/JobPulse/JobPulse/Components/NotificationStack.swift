import SwiftUI

/// The iOS lock-screen notification stack, rebuilt for the job feed.
///
/// The trick is a single `VStack` whose spacing goes negative when collapsed:
/// each card then sits behind the one above it with only `peek` points showing,
/// and expanding is a spring on one number rather than a layout swap. Because
/// the view identity never changes, cards slide apart instead of cross-fading.
///
/// Depth comes from three cues applied by index — scale, opacity and a slight
/// horizontal inset — which is what makes the collapsed group read as a pile of
/// cards rather than a list with small rows.
struct NotificationStack: View {
    enum Metrics {
        static let cardHeight: CGFloat = 78
        /// How much of each card behind the front one stays visible.
        static let peek: CGFloat = 11
        static let expandedSpacing: CGFloat = 10
        /// Cards beyond this are represented by the count badge only.
        static let maxVisible = 3
    }

    let stack: CompanyStack
    @Binding var expandedCompany: String?

    var savedIds: Set<Int>
    var onSelect: (Job) -> Void
    var onSave: (Job) -> Void
    var onDismiss: ((Job) -> Void)?

    private var isExpanded: Bool { expandedCompany == stack.company.slug }

    private var visibleJobs: [Job] {
        isExpanded ? stack.jobs : Array(stack.jobs.prefix(Metrics.maxVisible))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.s) {
            headerRow
            cardPile
        }
        .animation(Theme.Motion.stack, value: isExpanded)
        .accessibilityElement(children: .contain)
    }

    // MARK: Header

    private var headerRow: some View {
        Button {
            toggle()
        } label: {
            HStack(spacing: Theme.Spacing.s) {
                Text(stack.company.name)
                    .font(Theme.Typeface.caption)
                    .foregroundStyle(Theme.Palette.textSecondary)

                if stack.count > 1 {
                    Text("\(stack.count)")
                        .font(Theme.Typeface.micro)
                        .foregroundStyle(Theme.Palette.textPrimary)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Capsule().fill(Color.white.opacity(0.16)))
                }

                Spacer()

                if stack.count > 1 {
                    Label(
                        isExpanded ? "Show less" : "Show all",
                        systemImage: isExpanded ? "chevron.up" : "chevron.down"
                    )
                    .labelStyle(.trailingIcon)
                    .font(Theme.Typeface.micro)
                    .foregroundStyle(Theme.Palette.textTertiary)
                }
            }
            .padding(.horizontal, Theme.Spacing.xs)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(stack.count <= 1)
        .accessibilityLabel("\(stack.company.name), \(stack.count) roles")
        .accessibilityHint(stack.count > 1 ? (isExpanded ? "Collapse stack" : "Expand stack") : "")
    }

    // MARK: Cards

    private var cardPile: some View {
        VStack(spacing: isExpanded ? Metrics.expandedSpacing : collapsedSpacing) {
            ForEach(Array(visibleJobs.enumerated()), id: \.element.id) { index, job in
                card(for: job, at: index)
            }
        }
        .padding(.bottom, isExpanded ? 0 : trailingPeekAllowance)
        .contentShape(Rectangle())
        .onTapGesture {
            // Tapping anywhere on a collapsed pile fans it out; when it is
            // already open, taps belong to the individual cards.
            if !isExpanded, stack.count > 1 { toggle() }
        }
    }

    private func card(for job: Job, at index: Int) -> some View {
        // Spelled out rather than `onDismiss.map { … }`: a closure returning a
        // closure is a common place for type inference to give up.
        let dismiss: (() -> Void)?
        if let onDismiss {
            dismiss = { onDismiss(job) }
        } else {
            dismiss = nil
        }

        return SwipeableCard(
            onSave: { onSave(job) },
            onDismiss: dismiss,
            isEnabled: isExpanded || index == 0
        ) {
            JobNotificationCard(
                job: job,
                style: isExpanded ? .full : .compact,
                isSaved: savedIds.contains(job.id),
                showsSaveButton: isExpanded || index == 0,
                onSave: { onSave(job) }
            )
            .onTapGesture {
                if isExpanded || index == 0 {
                    onSelect(job)
                } else {
                    toggle()
                }
            }
        }
        .scaleEffect(scale(for: index), anchor: .top)
        .opacity(opacity(for: index))
        .padding(.horizontal, inset(for: index))
        .zIndex(Double(visibleJobs.count - index))
        .allowsHitTesting(isExpanded || index == 0)
        .accessibilityHidden(!isExpanded && index > 0)
    }

    // MARK: Depth

    /// Negative spacing is what buries each card behind the previous one.
    private var collapsedSpacing: CGFloat {
        -(Metrics.cardHeight - Metrics.peek)
    }

    /// The pile is `cardHeight` tall in layout terms, but the peeking cards
    /// draw below that; this reserves the difference so nothing is clipped.
    private var trailingPeekAllowance: CGFloat {
        CGFloat(max(0, visibleJobs.count - 1)) * Metrics.peek
    }

    private func scale(for index: Int) -> CGFloat {
        guard !isExpanded else { return 1 }
        return 1 - CGFloat(index) * 0.045
    }

    private func opacity(for index: Int) -> Double {
        guard !isExpanded else { return 1 }
        return max(0.35, 1 - Double(index) * 0.3)
    }

    private func inset(for index: Int) -> CGFloat {
        guard !isExpanded else { return 0 }
        return CGFloat(index) * 7
    }

    private func toggle() {
        withAnimation(Theme.Motion.stack) {
            expandedCompany = isExpanded ? nil : stack.company.slug
        }
        Haptics.play(.soft)
    }
}

// MARK: - Swipe actions

/// Drag a card left to dismiss it, right to save — the same grammar as the
/// notification actions on the lock screen.
struct SwipeableCard<Content: View>: View {
    var onSave: () -> Void
    var onDismiss: (() -> Void)?
    var isEnabled = true
    @ViewBuilder var content: Content

    @State private var offset: CGFloat = 0

    private let triggerDistance: CGFloat = 78

    var body: some View {
        ZStack {
            actionLayer
            content
                .offset(x: offset)
                .gesture(dragGesture)
        }
    }

    private var actionLayer: some View {
        HStack {
            actionIcon(
                systemName: "star.fill",
                tint: Theme.Palette.warning,
                active: offset > triggerDistance
            )
            .opacity(offset > 8 ? 1 : 0)

            Spacer()

            if onDismiss != nil {
                actionIcon(
                    systemName: "xmark",
                    tint: Theme.Palette.destructive,
                    active: offset < -triggerDistance
                )
                .opacity(offset < -8 ? 1 : 0)
            }
        }
        .padding(.horizontal, Theme.Spacing.l)
    }

    private func actionIcon(systemName: String, tint: Color, active: Bool) -> some View {
        Image(systemName: systemName)
            .font(.system(size: 15, weight: .bold))
            .foregroundStyle(active ? Theme.Palette.textPrimary : tint)
            .frame(width: 34, height: 34)
            .background(Circle().fill(tint.opacity(active ? 0.9 : 0.22)))
            .scaleEffect(active ? 1.15 : 1)
            .animation(Theme.Motion.interactive, value: active)
    }

    private var dragGesture: some Gesture {
        // `isEnabled` is checked inside rather than by swapping the gesture for
        // nil — `.gesture()` takes a concrete Gesture, so a conditional would
        // not type-check.
        DragGesture(minimumDistance: 12)
            .onChanged { value in
                guard isEnabled else { return }
                let raw = value.translation.width
                // Rubber-band past the trigger point so the card resists.
                let resisted = abs(raw) > triggerDistance
                    ? triggerDistance + (abs(raw) - triggerDistance) * 0.35
                    : abs(raw)
                let signed = raw < 0 ? -resisted : resisted
                offset = onDismiss == nil ? max(0, signed) : signed
            }
            .onEnded { _ in
                guard isEnabled else { return }
                if offset > triggerDistance {
                    onSave()
                } else if offset < -triggerDistance, let onDismiss {
                    onDismiss()
                }
                withAnimation(Theme.Motion.interactive) { offset = 0 }
            }
    }
}

// MARK: - Label style

struct TrailingIconLabelStyle: LabelStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: 4) {
            configuration.title
            configuration.icon
        }
    }
}

extension LabelStyle where Self == TrailingIconLabelStyle {
    static var trailingIcon: TrailingIconLabelStyle { TrailingIconLabelStyle() }
}

#Preview {
    @Previewable @State var expanded: String?
    ZStack {
        AuroraBackground()
        ScrollView {
            VStack(spacing: Theme.Spacing.l) {
                ForEach(CompanyStack.previewList) { stack in
                    NotificationStack(
                        stack: stack,
                        expandedCompany: $expanded,
                        savedIds: [],
                        onSelect: { _ in },
                        onSave: { _ in },
                        onDismiss: { _ in }
                    )
                }
            }
            .padding()
        }
    }
}
