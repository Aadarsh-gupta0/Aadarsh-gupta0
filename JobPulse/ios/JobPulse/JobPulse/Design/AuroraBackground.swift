import SwiftUI

/// Slow-drifting colour field behind every screen.
///
/// Glassmorphism has nothing to refract on a flat background, so the panels
/// need something moving and saturated underneath them. These blobs are heavily
/// blurred, which is why three of them are enough.
struct AuroraBackground: View {
    /// Set by the detail screen so the background picks up the company's accent.
    var tint: Color?

    @State private var drift = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        GeometryReader { proxy in
            let size = proxy.size

            ZStack {
                Theme.Palette.canvas.ignoresSafeArea()

                blob(
                    color: tint ?? Theme.Palette.auroraTop,
                    diameter: size.width * 1.15,
                    opacity: 0.55
                )
                .offset(
                    x: drift ? -size.width * 0.28 : -size.width * 0.16,
                    y: drift ? -size.height * 0.36 : -size.height * 0.28
                )

                blob(
                    color: Theme.Palette.auroraMid,
                    diameter: size.width * 1.0,
                    opacity: 0.45
                )
                .offset(
                    x: drift ? size.width * 0.34 : size.width * 0.22,
                    y: drift ? -size.height * 0.12 : -size.height * 0.02
                )

                blob(
                    color: Theme.Palette.auroraWarm,
                    diameter: size.width * 0.9,
                    opacity: 0.34
                )
                .offset(
                    x: drift ? -size.width * 0.20 : -size.width * 0.05,
                    y: drift ? size.height * 0.34 : size.height * 0.42
                )

                // Darkens the lower half so text over the feed keeps contrast.
                LinearGradient(
                    colors: [.clear, Theme.Palette.canvas.opacity(0.85)],
                    startPoint: .center,
                    endPoint: .bottom
                )
                .ignoresSafeArea()
                .allowsHitTesting(false)
            }
        }
        .ignoresSafeArea()
        .onAppear {
            guard !reduceMotion else { return }
            withAnimation(Theme.Motion.ambient) { drift = true }
        }
    }

    private func blob(color: Color, diameter: CGFloat, opacity: Double) -> some View {
        Circle()
            .fill(
                RadialGradient(
                    colors: [color.opacity(opacity), color.opacity(0)],
                    center: .center,
                    startRadius: 0,
                    endRadius: diameter / 2
                )
            )
            .frame(width: diameter, height: diameter)
            .blur(radius: 60)
    }
}

/// The outlined circles scattered around the greeting in the reference design.
struct BubbleField: View {
    var count: Int = 6

    @State private var floating = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    /// Fixed layout rather than random, so the composition is the same on every
    /// launch and does not fight the greeting text for attention.
    private let layout: [(x: CGFloat, y: CGFloat, size: CGFloat, delay: Double)] = [
        (0.10, 0.16, 26, 0.0),
        (0.24, 0.52, 18, 0.6),
        (0.44, 0.06, 22, 1.2),
        (0.70, 0.44, 16, 0.3),
        (0.86, 0.14, 30, 0.9),
        (0.62, 0.78, 12, 1.5)
    ]

    var body: some View {
        GeometryReader { proxy in
            ForEach(Array(layout.prefix(count).enumerated()), id: \.offset) { index, spec in
                Circle()
                    .strokeBorder(Color.white.opacity(0.22), lineWidth: 1)
                    .frame(width: spec.size, height: spec.size)
                    .position(x: proxy.size.width * spec.x, y: proxy.size.height * spec.y)
                    .offset(y: floating ? -6 : 6)
                    .animation(
                        reduceMotion
                            ? nil
                            : .easeInOut(duration: 3.2 + Double(index) * 0.4)
                                .repeatForever(autoreverses: true)
                                .delay(spec.delay),
                        value: floating
                    )
            }
        }
        .allowsHitTesting(false)
        .onAppear { floating = true }
    }
}

#Preview {
    ZStack {
        AuroraBackground()
        BubbleField()
        Text("Hi Aadarsh")
            .font(Theme.Typeface.greeting())
            .foregroundStyle(Theme.Palette.textPrimary)
    }
}
