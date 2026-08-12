"""A realistic sample set so the app has something to render before the first scrape.

These are illustrative postings, not live listings — `apply_url` points at each
company's real careers page rather than a specific requisition.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .scrapers.base import RawJob

_NOW = datetime.now(UTC)


def _ago(hours: float) -> datetime:
    return _NOW - timedelta(hours=hours)


SEED_JOBS: list[RawJob] = [
    RawJob(
        source="seed",
        source_id="seed-1",
        title="Product Designer, Intern",
        company_name="Google",
        apply_url="https://careers.google.com/jobs/results/",
        description_text=(
            "By applying to this position you will have an opportunity to share your preferred "
            "working location from the list below.\n\n"
            "As a Product Design Intern you will work end-to-end on features used by billions of "
            "people — from early discovery and user research through wireframes, high-fidelity "
            "prototypes in Figma, and hand-off to engineering. You will partner with researchers "
            "and product managers to shape user journeys and contribute to our design system."
        ),
        location="Bengaluru, India",
        employment_type_raw="Internship",
        tags=["design", "internship", "figma", "product design"],
        posted_at=_ago(2),
        company_logo_url="https://www.google.com/favicon.ico",
        company_website="https://about.google",
    ),
    RawJob(
        source="seed",
        source_id="seed-2",
        title="Senior Flutter Engineer",
        company_name="Google",
        apply_url="https://careers.google.com/jobs/results/",
        description_text=(
            "Join the Flutter team building the framework itself. You will write Dart, profile "
            "rendering performance across iOS and Android, and work on the widget layer used by "
            "millions of developers. Experience with cross-platform mobile development and a "
            "strong grasp of state management (Riverpod, BLoC) expected."
        ),
        location="Remote",
        remote_hint=True,
        salary_raw="$150,000 - $220,000",
        tags=["flutter", "dart", "mobile"],
        posted_at=_ago(5),
        company_logo_url="https://www.google.com/favicon.ico",
    ),
    RawJob(
        source="seed",
        source_id="seed-3",
        title="Product Designer",
        company_name="Figma",
        apply_url="https://www.figma.com/careers/",
        description_text=(
            "We are looking for a product designer to own end-to-end design for our editor "
            "surfaces. You will run design critique, build prototypes, contribute to design "
            "systems and tokens, and partner with user research on 0 to 1 explorations."
        ),
        location="Remote (US)",
        remote_hint=True,
        salary_raw="$149,000 - $200,000",
        tags=["product design", "design systems", "figma"],
        posted_at=_ago(9),
        company_website="https://figma.com",
    ),
    RawJob(
        source="seed",
        source_id="seed-4",
        title="UI/UX Design Intern",
        company_name="Razorpay",
        apply_url="https://razorpay.com/jobs/",
        description_text=(
            "Work alongside our design team on merchant-facing dashboards. You will create "
            "wireframes, run usability testing sessions, build interactive prototypes in Figma "
            "and help extend our design system. Portfolio required."
        ),
        location="Bengaluru, India",
        employment_type_raw="Internship",
        salary_raw="₹40,000 - ₹60,000",
        tags=["ui/ux", "internship", "figma"],
        posted_at=_ago(14),
        company_website="https://razorpay.com",
    ),
    RawJob(
        source="seed",
        source_id="seed-5",
        title="Flutter Developer Intern",
        company_name="Swiggy",
        apply_url="https://careers.swiggy.com/",
        description_text=(
            "Build and ship features in our Flutter consumer app. You will work with Dart, "
            "Firebase, BLoC and our internal design system, and own small features end to end "
            "under the guidance of a senior engineer."
        ),
        location="Bengaluru, India",
        employment_type_raw="Internship",
        salary_raw="₹35,000 - ₹50,000",
        tags=["flutter", "dart", "internship"],
        posted_at=_ago(20),
        company_website="https://swiggy.com",
    ),
    RawJob(
        source="seed",
        source_id="seed-6",
        title="Senior Product Designer, Growth",
        company_name="Canva",
        apply_url="https://www.lifeatcanva.com/en/jobs/",
        description_text=(
            "Own the design strategy for our growth surfaces. You will map user journeys, "
            "prototype quickly, run experiments with data scientists and shape information "
            "architecture across onboarding."
        ),
        location="Remote (APAC)",
        remote_hint=True,
        tags=["product design", "growth"],
        posted_at=_ago(26),
        company_website="https://canva.com",
    ),
    RawJob(
        source="seed",
        source_id="seed-7",
        title="Mobile Engineer (Flutter)",
        company_name="Postman",
        apply_url="https://www.postman.com/company/careers/",
        description_text=(
            "Help bring the Postman experience to mobile. Flutter and Dart day to day, plus "
            "platform channels into native iOS and Android. You will care about frame budgets "
            "and about the craft of an interface."
        ),
        location="Bengaluru, India (Hybrid)",
        salary_raw="₹25L - ₹45L",
        tags=["flutter", "dart", "mobile"],
        posted_at=_ago(31),
        company_website="https://postman.com",
    ),
    RawJob(
        source="seed",
        source_id="seed-8",
        title="Interaction Designer",
        company_name="Atlassian",
        apply_url="https://www.atlassian.com/company/careers",
        description_text=(
            "We need an interaction designer who thinks in motion. You will define micro "
            "interactions, contribute motion design guidance to our design system, and prototype "
            "in Figma and code."
        ),
        location="Remote (India)",
        remote_hint=True,
        tags=["interaction design", "motion design", "ui/ux"],
        posted_at=_ago(38),
        company_website="https://atlassian.com",
    ),
    RawJob(
        source="seed",
        source_id="seed-9",
        title="UX Researcher & Designer",
        company_name="Zomato",
        apply_url="https://www.zomato.com/careers",
        description_text=(
            "Blend user research and interface design. You will run usability testing, "
            "synthesise findings into user journeys, and turn them into wireframes and "
            "high fidelity screens."
        ),
        location="Gurugram, India",
        tags=["user research", "ui/ux"],
        posted_at=_ago(44),
        company_website="https://zomato.com",
    ),
    RawJob(
        source="seed",
        source_id="seed-10",
        title="Research Intern — Avionics Software",
        company_name="ISRO",
        apply_url="https://www.isro.gov.in/Careers.html",
        description_text=(
            "Research internship with the avionics software group. Candidates pursuing B.Tech "
            "or M.Tech may apply. Work spans embedded systems verification and simulation "
            "tooling under the guidance of a research scientist."
        ),
        location="Bengaluru, India",
        employment_type_raw="Internship",
        tags=["research", "internship", "government"],
        posted_at=_ago(50),
        company_website="https://www.isro.gov.in",
    ),
    RawJob(
        source="seed",
        source_id="seed-11",
        title="Design Engineer (SwiftUI)",
        company_name="Linear",
        apply_url="https://linear.app/careers",
        description_text=(
            "Sit between design and engineering. You will prototype in SwiftUI, own our design "
            "tokens, and hold the line on visual design quality across the product."
        ),
        location="Remote",
        remote_hint=True,
        salary_raw="$130,000 - $180,000",
        tags=["design systems", "swiftui", "ui/ux"],
        posted_at=_ago(58),
        company_website="https://linear.app",
    ),
    RawJob(
        source="seed",
        source_id="seed-12",
        title="Product Design Intern (Summer)",
        company_name="Notion",
        apply_url="https://www.notion.so/careers",
        description_text=(
            "A twelve week product design internship. You will be paired with a mentor, ship a "
            "real feature end to end, and present your work at design critique. We look for "
            "portfolios that show thinking, not just screens."
        ),
        location="Remote",
        remote_hint=True,
        employment_type_raw="Internship",
        tags=["product design", "internship"],
        posted_at=_ago(66),
        company_website="https://notion.so",
    ),
    RawJob(
        source="seed",
        source_id="seed-13",
        title="Flutter Developer",
        company_name="Groww",
        apply_url="https://groww.in/careers",
        description_text=(
            "Own screens in the Groww app. Strong Dart fundamentals, comfort with Riverpod or "
            "GetX, and an eye for the details that make an investing app feel trustworthy."
        ),
        location="Bengaluru, India",
        salary_raw="₹18L - ₹32L",
        tags=["flutter", "dart", "fintech"],
        posted_at=_ago(72),
        company_website="https://groww.in",
    ),
    RawJob(
        source="seed",
        source_id="seed-14",
        title="Visual Designer, Brand",
        company_name="Google",
        apply_url="https://careers.google.com/jobs/results/",
        description_text=(
            "Shape the visual design language for a product surface used worldwide. Works "
            "closely with the design systems team on typography, colour and accessibility."
        ),
        location="Hyderabad, India",
        tags=["visual design", "brand"],
        posted_at=_ago(80),
        company_logo_url="https://www.google.com/favicon.ico",
    ),
]
