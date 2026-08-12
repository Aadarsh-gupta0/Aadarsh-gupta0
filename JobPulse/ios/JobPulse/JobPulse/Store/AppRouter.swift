import Foundation
import Observation
import SwiftUI

enum AppTab: String, CaseIterable, Identifiable {
    case home
    case incoming
    case saved
    case profile

    var id: String { rawValue }

    var title: String {
        switch self {
        case .home: "For You"
        case .incoming: "Incoming"
        case .saved: "Saved"
        case .profile: "You"
        }
    }

    var symbolName: String {
        switch self {
        case .home: "sparkles.rectangle.stack"
        case .incoming: "bell.badge"
        case .saved: "bookmark"
        case .profile: "person.crop.circle"
        }
    }
}

/// Navigation state, including the deep link a tapped notification carries.
@MainActor
@Observable
final class AppRouter {
    var selectedTab: AppTab = .home
    var homePath = NavigationPath()
    var incomingPath = NavigationPath()
    var savedPath = NavigationPath()

    var isSearching = false

    func select(_ tab: AppTab) {
        guard tab != selectedTab else {
            popToRoot(tab)
            return
        }
        selectedTab = tab
        Haptics.play(.light)
    }

    /// Safe to call before the UI exists: `incomingPath` is plain state, and
    /// `IncomingView`'s `NavigationStack` adopts it when the view is created.
    func openJob(id: Int) {
        selectedTab = .incoming
        isSearching = false
        incomingPath.append(JobRoute.detail(id))
    }

    func handle(url: URL) {
        // jobpulse://job/123
        guard url.scheme == "jobpulse" else { return }
        if url.host == "job", let id = Int(url.lastPathComponent) {
            openJob(id: id)
        }
    }

    private func popToRoot(_ tab: AppTab) {
        switch tab {
        case .home: homePath = NavigationPath()
        case .incoming: incomingPath = NavigationPath()
        case .saved: savedPath = NavigationPath()
        case .profile: break
        }
    }
}

enum JobRoute: Hashable {
    case detail(Int)
    case company(String)
}
