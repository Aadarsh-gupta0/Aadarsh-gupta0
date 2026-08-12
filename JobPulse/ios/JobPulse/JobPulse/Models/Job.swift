import SwiftUI

// MARK: - Company

struct CompanyBrief: Codable, Hashable, Identifiable, Sendable {
    var slug: String
    var name: String
    var logoUrl: String?

    var id: String { slug }

    /// Fallback for the avatar when a source gives us no logo.
    var monogram: String {
        let words = name.split(separator: " ").prefix(2)
        let letters = words.compactMap { $0.first.map(String.init) }
        return letters.joined().uppercased()
    }
}

/// One row in the detail screen's "Stats" block. A named struct rather than a
/// tuple because `ForEach(_:id:)` needs a key path, and Swift has no key paths
/// into tuple elements.
struct CompanyStat: Identifiable, Hashable, Sendable {
    let label: String
    let value: String

    var id: String { label }
}

struct CompanyLink: Identifiable, Hashable, Sendable {
    let label: String
    let url: URL

    var id: String { label }
}

struct CompanyDetail: Codable, Hashable, Identifiable, Sendable {
    var id: Int
    var slug: String
    var name: String
    var logoUrl: String?
    var website: String?
    var careersUrl: String?
    var linkedinUrl: String?
    var description: String?
    var industry: String?
    var headquarters: String?
    var employeeCount: String?
    var foundedYear: Int?
    var openRoles: Int

    /// Rows for the detail screen's "Stats" block, skipping anything unknown.
    var stats: [CompanyStat] {
        var rows: [CompanyStat] = []
        if let industry { rows.append(CompanyStat(label: "Industry", value: industry)) }
        if let headquarters { rows.append(CompanyStat(label: "HQ", value: headquarters)) }
        if let employeeCount { rows.append(CompanyStat(label: "Size", value: employeeCount)) }
        if let foundedYear {
            rows.append(CompanyStat(label: "Founded", value: String(foundedYear)))
        }
        rows.append(CompanyStat(label: "Open roles", value: String(openRoles)))
        return rows
    }

    var links: [CompanyLink] {
        var rows: [CompanyLink] = []
        if let website, let url = URL(string: website) {
            rows.append(CompanyLink(label: "Website", url: url))
        }
        if let careersUrl, let url = URL(string: careersUrl) {
            rows.append(CompanyLink(label: "Careers", url: url))
        }
        if let linkedinUrl, let url = URL(string: linkedinUrl) {
            rows.append(CompanyLink(label: "LinkedIn", url: url))
        }
        return rows
    }
}

// MARK: - Match

struct InterestMatch: Codable, Hashable, Identifiable, Sendable {
    var profileSlug: String
    var label: String
    var accent: String
    var score: Double
    var matchedTerms: [String]

    var id: String { profileSlug }
    var color: Color { Color(hex: accent) }

    var percentText: String { "\(Int((score * 100).rounded()))%" }
}

// MARK: - Job

struct Job: Codable, Hashable, Identifiable, Sendable {
    var id: Int
    var title: String
    var company: CompanyBrief
    var location: String?
    var isRemote: Bool
    var isInternship: Bool
    var employmentType: String?
    var seniority: String?
    var salaryDisplay: String?
    var tags: [String]
    var postedAt: Date?
    var source: String
    var applyUrl: String
    var topScore: Double
    var matches: [InterestMatch]
    var excerpt: String

    // Present only on the detail endpoint.
    var descriptionText: String?
    var companyDetail: CompanyDetail?
    var related: [Job]?

    var primaryMatch: InterestMatch? { matches.first }
    var accentColor: Color { primaryMatch?.color ?? Theme.Palette.accent }
    var applyURL: URL? { URL(string: applyUrl) }

    /// "2h ago" / "Just now" — the timestamp shown on each notification card.
    var postedRelative: String {
        guard let postedAt else { return "" }
        let seconds = Date().timeIntervalSince(postedAt)
        if seconds < 60 { return "Just now" }
        if seconds < 3600 { return "\(Int(seconds / 60))m ago" }
        if seconds < 86_400 { return "\(Int(seconds / 3600))h ago" }
        if seconds < 604_800 { return "\(Int(seconds / 86_400))d ago" }
        return postedAt.formatted(.dateTime.day().month(.abbreviated))
    }

    var isNew: Bool {
        guard let postedAt else { return false }
        return Date().timeIntervalSince(postedAt) < 48 * 3600
    }

    /// Short facts rendered as pills under the title.
    var attributes: [String] {
        var values: [String] = []
        if isInternship { values.append("Internship") }
        if isRemote {
            values.append("Remote")
        } else if let location, !location.isEmpty {
            values.append(location)
        }
        if let salaryDisplay, !salaryDisplay.isEmpty { values.append(salaryDisplay) }
        if let seniority, !isInternship, seniority != "mid" { values.append(seniority.capitalized) }
        return values
    }
}

// MARK: - Feed envelopes

struct FeedResponse: Codable, Sendable {
    var items: [Job]
    var nextCursor: String?
    var total: Int
    var generatedAt: Date
}

struct CompanyStack: Codable, Hashable, Identifiable, Sendable {
    var company: CompanyBrief
    var jobs: [Job]
    var topScore: Double
    var latestPostedAt: Date?

    var id: String { company.slug }
    var count: Int { jobs.count }

    /// Drives the tint of the stack — the strongest match in the group.
    var accentColor: Color {
        jobs.first?.accentColor ?? Theme.Palette.accent
    }
}

struct StackedFeedResponse: Codable, Sendable {
    var stacks: [CompanyStack]
    var generatedAt: Date
}

// MARK: - Interests

struct Interest: Codable, Hashable, Identifiable, Sendable {
    var slug: String
    var label: String
    var tagline: String
    var accent: String

    var id: String { slug }
    var color: Color { Color(hex: accent) }

    var symbolName: String {
        switch slug {
        case "flutter": "hammer.fill"
        case "ui_ux": "square.on.circle.fill"
        case "product_design": "sparkles"
        case "govt_research": "building.columns.fill"
        default: "star.fill"
        }
    }
}

// MARK: - Device

struct DeviceProfile: Codable, Hashable, Sendable {
    var id: Int
    var installId: String?
    var displayName: String?
    var interests: [String]
    var pushEnabled: Bool
    var internshipsOnly: Bool
    var minScore: Double
    var timezone: String
    var quietHoursEnabled: Bool
    var createdAt: Date
    var lastSeenAt: Date
}

struct DeviceRegistration: Codable, Sendable {
    var apnsToken: String
    var installId: String?
    var displayName: String?
    var interests: [String]
    var pushEnabled: Bool = true
    var internshipsOnly: Bool = false
    var minScore: Double = 0.55
    var timezone: String = TimeZone.current.identifier
    var quietHoursEnabled: Bool = true
    var appVersion: String?
    var environment: String = "sandbox"
}

struct DevicePatch: Codable, Sendable {
    var displayName: String?
    var interests: [String]?
    var pushEnabled: Bool?
    var internshipsOnly: Bool?
    var minScore: Double?
    var timezone: String?
    var quietHoursEnabled: Bool?
    var appVersion: String?
}

// MARK: - Saved

enum SaveState: String, Codable, CaseIterable, Sendable {
    case saved, applied, dismissed

    var label: String {
        switch self {
        case .saved: "Saved"
        case .applied: "Applied"
        case .dismissed: "Dismissed"
        }
    }

    var symbolName: String {
        switch self {
        case .saved: "bookmark.fill"
        case .applied: "paperplane.fill"
        case .dismissed: "xmark"
        }
    }
}

struct SavedJob: Codable, Hashable, Identifiable, Sendable {
    var job: Job
    var state: SaveState
    var note: String?
    var createdAt: Date

    var id: Int { job.id }
}

struct SaveRequest: Codable, Sendable {
    var jobId: Int
    var state: SaveState
    var note: String?
}
