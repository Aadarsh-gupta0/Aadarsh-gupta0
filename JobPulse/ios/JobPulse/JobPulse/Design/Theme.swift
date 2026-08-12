import SwiftUI

/// Design tokens for the app.
///
/// The palette is dark-first on purpose: glassmorphism relies on bright,
/// saturated light bleeding through a frosted panel, and that reads as mud on a
/// light ground. `RootView` pins the colour scheme to dark to match.
enum Theme {

    // MARK: - Colour

    enum Palette {
        /// Base canvas the aurora blobs sit on.
        static let canvas = Color(red: 0.039, green: 0.039, blue: 0.047)
        static let canvasElevated = Color(red: 0.07, green: 0.07, blue: 0.082)

        static let textPrimary = Color.white
        static let textSecondary = Color.white.opacity(0.62)
        static let textTertiary = Color.white.opacity(0.38)

        /// The blue on the selected "All" chip in the reference design.
        static let accent = Color(red: 0.18, green: 0.48, blue: 1.0)

        static let flutter = Color(red: 0.26, green: 0.85, blue: 0.68)
        static let uiux = Color(red: 0.49, green: 0.55, blue: 1.0)
        static let productDesign = Color(red: 1.0, green: 0.49, blue: 0.61)
        static let govtResearch = Color(red: 0.96, green: 0.77, blue: 0.32)

        static let positive = Color(red: 0.30, green: 0.85, blue: 0.55)
        static let warning = Color(red: 1.0, green: 0.72, blue: 0.30)
        static let destructive = Color(red: 1.0, green: 0.34, blue: 0.36)

        /// Aurora blobs behind the glass. Their blur is what the panels refract.
        static let auroraTop = Color(red: 0.36, green: 0.30, blue: 0.95)
        static let auroraMid = Color(red: 0.05, green: 0.55, blue: 0.85)
        static let auroraWarm = Color(red: 0.95, green: 0.30, blue: 0.52)
    }

    // MARK: - Glass

    enum Glass {
        /// Tint layered over the material so panels keep their own body.
        static let fill = Color.white.opacity(0.07)
        static let fillRaised = Color.white.opacity(0.12)
        static let fillPressed = Color.white.opacity(0.16)

        /// A single light source at the top-left, which is what sells the
        /// "pane of glass" read — a uniform border looks like a plain outline.
        static let borderGradient = LinearGradient(
            colors: [
                Color.white.opacity(0.40),
                Color.white.opacity(0.10),
                Color.white.opacity(0.04),
                Color.white.opacity(0.16)
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )

        static let specularHighlight = LinearGradient(
            colors: [Color.white.opacity(0.18), Color.white.opacity(0.0)],
            startPoint: .top,
            endPoint: .center
        )

        static let shadow = Color.black.opacity(0.45)
    }

    // MARK: - Metrics

    enum Radius {
        static let small: CGFloat = 12
        static let card: CGFloat = 22
        static let sheet: CGFloat = 32
        static let pill: CGFloat = 100
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let s: CGFloat = 8
        static let m: CGFloat = 14
        static let l: CGFloat = 20
        static let xl: CGFloat = 28
        static let xxl: CGFloat = 40

        /// Room left at the bottom of scroll views so the floating tab bar
        /// never covers the last row.
        static let tabBarClearance: CGFloat = 108
    }

    // MARK: - Type

    enum Typeface {
        /// The serif greeting from the reference design.
        static func greeting(_ size: CGFloat = 42) -> Font {
            .system(size: size, weight: .regular, design: .serif)
        }

        static let sectionTitle = Font.system(size: 22, weight: .bold)
        static let cardTitle = Font.system(size: 16, weight: .semibold)
        static let cardBody = Font.system(size: 14, weight: .regular)
        static let caption = Font.system(size: 12, weight: .medium)
        static let micro = Font.system(size: 11, weight: .semibold)
        static let numeric = Font.system(size: 13, weight: .semibold).monospacedDigit()
    }

    // MARK: - Motion

    enum Motion {
        /// Used for anything the user directly manipulates.
        static let interactive = Animation.spring(response: 0.34, dampingFraction: 0.78)
        /// Stack expand / collapse — slightly looser so cards feel weighted.
        static let stack = Animation.spring(response: 0.44, dampingFraction: 0.82)
        static let gentle = Animation.easeInOut(duration: 0.25)
        /// Slow drift of the background blobs.
        static let ambient = Animation.easeInOut(duration: 14).repeatForever(autoreverses: true)
    }
}

// MARK: - Hex bridging

extension Color {
    /// Builds a colour from the `#RRGGBB` strings the API sends for each
    /// interest profile, so server and app never drift apart on accent colour.
    init(hex: String) {
        let cleaned = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var value: UInt64 = 0
        Scanner(string: cleaned).scanHexInt64(&value)

        let r, g, b, a: Double
        switch cleaned.count {
        case 6:
            r = Double((value & 0xFF0000) >> 16) / 255
            g = Double((value & 0x00FF00) >> 8) / 255
            b = Double(value & 0x0000FF) / 255
            a = 1
        case 8:
            r = Double((value & 0xFF00_0000) >> 24) / 255
            g = Double((value & 0x00FF_0000) >> 16) / 255
            b = Double((value & 0x0000_FF00) >> 8) / 255
            a = Double(value & 0x0000_00FF) / 255
        default:
            r = 1; g = 1; b = 1; a = 1
        }
        self.init(.sRGB, red: r, green: g, blue: b, opacity: a)
    }
}
