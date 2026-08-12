import SwiftUI

/// The glassmorphism panel used by every surface in the app.
///
/// Four layers, in order, are what separate this from a plain translucent
/// rectangle:
///   1. a system material, so the aurora behind it is genuinely blurred;
///   2. a white tint, giving the pane its own body;
///   3. a top-biased specular highlight, implying a light source;
///   4. a directional hairline border that is brightest where that light hits.
struct GlassPanel: ViewModifier {
    var cornerRadius: CGFloat = Theme.Radius.card
    var fill: Color = Theme.Glass.fill
    var strokeWidth: CGFloat = 1
    var shadowRadius: CGFloat = 18
    var showsHighlight: Bool = true

    func body(content: Content) -> some View {
        content
            .background {
                shape
                    .fill(.ultraThinMaterial)
                    .overlay(shape.fill(fill))
                    .overlay {
                        if showsHighlight {
                            shape
                                .fill(Theme.Glass.specularHighlight)
                                .blendMode(.plusLighter)
                                .allowsHitTesting(false)
                        }
                    }
            }
            .overlay {
                shape.strokeBorder(Theme.Glass.borderGradient, lineWidth: strokeWidth)
            }
            .clipShape(shape)
            .shadow(color: Theme.Glass.shadow, radius: shadowRadius, x: 0, y: shadowRadius / 2)
    }

    private var shape: RoundedRectangle {
        RoundedRectangle(cornerRadius: cornerRadius, style: .continuous)
    }
}

extension View {
    /// Standard frosted panel.
    func glassPanel(
        cornerRadius: CGFloat = Theme.Radius.card,
        fill: Color = Theme.Glass.fill,
        shadowRadius: CGFloat = 18,
        showsHighlight: Bool = true
    ) -> some View {
        modifier(
            GlassPanel(
                cornerRadius: cornerRadius,
                fill: fill,
                shadowRadius: shadowRadius,
                showsHighlight: showsHighlight
            )
        )
    }

    /// Capsule variant for chips and small controls.
    func glassPill(fill: Color = Theme.Glass.fill) -> some View {
        modifier(
            GlassPanel(
                cornerRadius: Theme.Radius.pill,
                fill: fill,
                shadowRadius: 8,
                showsHighlight: false
            )
        )
    }

    /// Adds a coloured bloom behind a panel — used to tint a card by the
    /// interest profile that matched it.
    func accentBloom(_ color: Color, radius: CGFloat = 40, opacity: Double = 0.30) -> some View {
        background {
            RoundedRectangle(cornerRadius: Theme.Radius.card, style: .continuous)
                .fill(color)
                .blur(radius: radius)
                .opacity(opacity)
                .allowsHitTesting(false)
        }
    }
}

/// Button style that presses the glass in slightly, the way a physical pane
/// would flex — scale alone reads as a sticker.
struct GlassButtonStyle: ButtonStyle {
    var cornerRadius: CGFloat = Theme.Radius.pill
    var tint: Color?

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .glassPanel(
                cornerRadius: cornerRadius,
                fill: configuration.isPressed
                    ? Theme.Glass.fillPressed
                    : (tint?.opacity(0.28) ?? Theme.Glass.fillRaised),
                shadowRadius: configuration.isPressed ? 6 : 14
            )
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .animation(Theme.Motion.interactive, value: configuration.isPressed)
    }
}
