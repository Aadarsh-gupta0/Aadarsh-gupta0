import SwiftUI
#if canImport(UIKit)
import UIKit
#endif

/// Thin wrapper so feedback calls read the same everywhere and stay off other
/// platforms.
enum Haptics {
    enum Style {
        case light, medium, soft, rigid
        case success, warning, failure
        case selection
    }

    static func play(_ style: Style) {
        #if canImport(UIKit) && !os(watchOS)
        switch style {
        case .light:
            UIImpactFeedbackGenerator(style: .light).impactOccurred()
        case .medium:
            UIImpactFeedbackGenerator(style: .medium).impactOccurred()
        case .soft:
            UIImpactFeedbackGenerator(style: .soft).impactOccurred()
        case .rigid:
            UIImpactFeedbackGenerator(style: .rigid).impactOccurred()
        case .success:
            UINotificationFeedbackGenerator().notificationOccurred(.success)
        case .warning:
            UINotificationFeedbackGenerator().notificationOccurred(.warning)
        case .failure:
            UINotificationFeedbackGenerator().notificationOccurred(.error)
        case .selection:
            UISelectionFeedbackGenerator().selectionChanged()
        }
        #endif
    }
}
