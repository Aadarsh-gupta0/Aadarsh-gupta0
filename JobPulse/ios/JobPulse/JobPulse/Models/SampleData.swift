import Foundation

/// Preview fixtures. Keeping these in the app target (rather than a test one)
/// means every `#Preview` renders without a running backend.
extension Job {
    static func sample(
        id: Int,
        title: String,
        company: String,
        slug: String? = nil,
        location: String? = "Bengaluru, India",
        isRemote: Bool = false,
        isInternship: Bool = false,
        salary: String? = nil,
        hoursAgo: Double = 2,
        profile: (slug: String, label: String, accent: String) = (
            "flutter", "Flutter Dev", "#43D9AD"
        ),
        score: Double = 0.92,
        terms: [String] = ["Flutter", "Dart"],
        excerpt: String = "By applying to this position you will have an opportunity to share your preferred working location."
    ) -> Job {
        Job(
            id: id,
            title: title,
            company: CompanyBrief(
                slug: slug ?? company.lowercased().replacingOccurrences(of: " ", with: "-"),
                name: company,
                logoUrl: nil
            ),
            location: location,
            isRemote: isRemote,
            isInternship: isInternship,
            employmentType: isInternship ? "internship" : "full_time",
            seniority: isInternship ? "intern" : "mid",
            salaryDisplay: salary,
            tags: terms.map { $0.lowercased() },
            postedAt: Date().addingTimeInterval(-hoursAgo * 3600),
            source: "seed",
            applyUrl: "https://example.com/apply/\(id)",
            topScore: score,
            matches: [
                InterestMatch(
                    profileSlug: profile.slug,
                    label: profile.label,
                    accent: profile.accent,
                    score: score,
                    matchedTerms: terms
                )
            ],
            excerpt: excerpt,
            descriptionText: """
                \(excerpt)

                As part of this role you will work end-to-end on features used by \
                a very large number of people — from early discovery and user \
                research through wireframes, high-fidelity prototypes, and \
                hand-off to engineering.

                Requirements
                • A portfolio that shows your thinking, not only final screens
                • Comfort with ambiguity and 0 to 1 problems
                • Strong written communication
                """,
            companyDetail: nil,
            related: nil
        )
    }

    static let preview = sample(
        id: 1,
        title: "Senior Flutter Engineer",
        company: "Google",
        location: "Remote",
        isRemote: true,
        salary: "$150k – $220k",
        hoursAgo: 2
    )

    static let previewInternship = sample(
        id: 2,
        title: "Product Designer, Intern",
        company: "Google",
        isInternship: true,
        hoursAgo: 5,
        profile: ("product_design", "Product Design", "#FF7C9C"),
        score: 0.88,
        terms: ["Product Designer", "Figma", "user research"]
    )

    static let previewList: [Job] = [
        preview,
        previewInternship,
        sample(
            id: 3,
            title: "UI/UX Design Intern",
            company: "Razorpay",
            isInternship: true,
            salary: "₹40,000 – ₹60,000",
            hoursAgo: 14,
            profile: ("ui_ux", "UI / UX", "#7C8CFF"),
            score: 0.81,
            terms: ["UI/UX", "Figma", "wireframing"]
        ),
        sample(
            id: 4,
            title: "Product Designer",
            company: "Figma",
            location: "Remote (US)",
            isRemote: true,
            salary: "$149k – $200k",
            hoursAgo: 20,
            profile: ("product_design", "Product Design", "#FF7C9C"),
            score: 0.95,
            terms: ["Product Designer", "design systems"]
        ),
        sample(
            id: 5,
            title: "Flutter Developer Intern",
            company: "Swiggy",
            isInternship: true,
            salary: "₹35,000 – ₹50,000",
            hoursAgo: 30,
            score: 0.86,
            terms: ["Flutter", "Dart", "Firebase"]
        )
    ]

    static let previewDetail: Job = {
        var job = preview
        job.companyDetail = CompanyDetail(
            id: 1,
            slug: "google",
            name: "Google",
            logoUrl: nil,
            website: "https://about.google",
            careersUrl: "https://careers.google.com",
            linkedinUrl: "https://www.linkedin.com/company/google",
            description:
                "A technology company focused on search, advertising, cloud infrastructure and consumer devices.",
            industry: "Technology",
            headquarters: "Mountain View, CA",
            employeeCount: "180,000+",
            foundedYear: 1998,
            openRoles: 3
        )
        job.related = [previewInternship]
        return job
    }()
}

extension CompanyStack {
    static let previewList: [CompanyStack] = [
        CompanyStack(
            company: CompanyBrief(slug: "google", name: "Google", logoUrl: nil),
            jobs: [
                .preview,
                .previewInternship,
                .sample(
                    id: 6,
                    title: "Visual Designer, Brand",
                    company: "Google",
                    location: "Hyderabad, India",
                    hoursAgo: 40,
                    profile: ("ui_ux", "UI / UX", "#7C8CFF"),
                    score: 0.72,
                    terms: ["visual design"]
                )
            ],
            topScore: 0.95,
            latestPostedAt: Date().addingTimeInterval(-7200)
        ),
        CompanyStack(
            company: CompanyBrief(slug: "figma", name: "Figma", logoUrl: nil),
            jobs: [Job.previewList[3]],
            topScore: 0.95,
            latestPostedAt: Date().addingTimeInterval(-72_000)
        ),
        CompanyStack(
            company: CompanyBrief(slug: "razorpay", name: "Razorpay", logoUrl: nil),
            jobs: [Job.previewList[2]],
            topScore: 0.81,
            latestPostedAt: Date().addingTimeInterval(-50_400)
        )
    ]
}

extension SavedJob {
    static let previewList: [SavedJob] = [
        SavedJob(job: .preview, state: .saved, note: nil, createdAt: .now),
        SavedJob(
            job: .previewInternship,
            state: .applied,
            note: "Referred by Ananya",
            createdAt: .now.addingTimeInterval(-86_400)
        )
    ]
}
