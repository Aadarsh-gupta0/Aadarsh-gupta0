"""Interest profiles.

Each profile is a bag of weighted regex terms plus a list of hard negatives. The
weights were tuned so that a job whose *title* names the discipline outright
("Flutter Developer", "Product Designer") saturates the score, while a job that
only mentions the skill deep in a requirements list lands somewhere in the
middle — high enough to show in the feed, low enough not to buzz the phone.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Terms that disqualify a posting no matter which profile is being scored.
GLOBAL_EXCLUDE: tuple[str, ...] = (
    r"business development",
    r"sales (executive|manager|representative|associate)",
    r"\brecruiter\b",
    r"talent acquisition",
    r"\bnurse\b",
    r"\bteacher\b",
    r"insurance agent",
    r"data entry",
    r"customer (support|success) (executive|representative)",
)


@dataclass(frozen=True)
class Term:
    pattern: str
    weight: float
    label: str | None = None

    @property
    def display(self) -> str:
        return self.label or self.pattern


@dataclass(frozen=True)
class InterestProfile:
    slug: str
    label: str
    tagline: str
    accent: str  # hex, mirrored by the iOS theme
    include: tuple[Term, ...]
    exclude: tuple[str, ...] = ()
    # A profile only scores if at least one of these anchors is present. It is
    # what stops "Product Manager (works closely with designers)" from being
    # served as a product-design role.
    anchors: tuple[str, ...] = ()
    saturation: float = 4.0
    keywords_for_search: tuple[str, ...] = field(default=())


FLUTTER = InterestProfile(
    slug="flutter",
    label="Flutter Dev",
    tagline="Flutter, Dart and cross-platform mobile",
    accent="#43D9AD",
    include=(
        Term(r"\bflutter\b", 1.0, "Flutter"),
        Term(r"\bflutterflow\b", 0.7, "FlutterFlow"),
        Term(r"\bdart\b", 0.85, "Dart"),
        Term(r"\briverpod\b", 0.6, "Riverpod"),
        Term(r"\bbloc\b", 0.45, "BLoC"),
        Term(r"\bgetx\b", 0.45, "GetX"),
        Term(r"\bmelos\b", 0.3, "Melos"),
        Term(r"cross[- ]platform", 0.5, "cross-platform"),
        Term(r"mobile (app|application)? ?develop(er|ment)", 0.6, "mobile development"),
        Term(r"\bandroid\b", 0.3, "Android"),
        Term(r"\bios\b", 0.3, "iOS"),
        Term(r"\bfirebase\b", 0.35, "Firebase"),
        Term(r"\bapp develop(er|ment)\b", 0.45, "app development"),
        Term(r"\bswiftui\b", 0.3, "SwiftUI"),
        Term(r"\bjetpack compose\b", 0.3, "Jetpack Compose"),
        Term(r"\breact native\b", 0.3, "React Native"),
    ),
    exclude=(r"\bflutter\s?wave\b",),
    anchors=(
        r"\bflutter\b",
        r"\bdart\b",
        r"mobile (app|application)? ?develop",
        r"\bandroid\b",
        r"\bios\b",
        r"\breact native\b",
        r"cross[- ]platform",
    ),
    saturation=4.0,
    keywords_for_search=("flutter developer", "flutter intern", "dart developer"),
)

UI_UX = InterestProfile(
    slug="ui_ux",
    label="UI / UX",
    tagline="Interface, interaction and experience design",
    accent="#7C8CFF",
    include=(
        Term(r"\bui\s?/?\s?ux\b", 1.0, "UI/UX"),
        Term(r"\bux designer\b", 1.0, "UX Designer"),
        Term(r"\bui designer\b", 1.0, "UI Designer"),
        Term(r"user experience", 0.8, "user experience"),
        Term(r"user interface", 0.7, "user interface"),
        Term(r"interaction design", 0.8, "interaction design"),
        Term(r"visual design", 0.6, "visual design"),
        Term(r"design system", 0.7, "design systems"),
        Term(r"\bfigma\b", 0.7, "Figma"),
        Term(r"adobe xd", 0.45, "Adobe XD"),
        Term(r"\bprototyp\w*", 0.5, "prototyping"),
        Term(r"\bwireframe\w*", 0.5, "wireframing"),
        Term(r"usability (test|research|studies)", 0.55, "usability testing"),
        Term(r"user research", 0.6, "user research"),
        Term(r"motion design", 0.4, "motion design"),
        Term(r"design token", 0.4, "design tokens"),
        Term(r"\baccessibility\b", 0.3, "accessibility"),
        Term(r"human interface guidelines", 0.4, "HIG"),
    ),
    exclude=(
        r"product manager",
        r"program manager",
        r"graphic design(er)? (for )?(print|packaging)",
    ),
    anchors=(
        r"\bdesign(er)?\b",
        r"\bux\b",
        r"\bui\b",
        r"\bfigma\b",
        r"user research",
    ),
    saturation=4.0,
    keywords_for_search=("ux designer", "ui designer intern", "product design intern"),
)

PRODUCT_DESIGN = InterestProfile(
    slug="product_design",
    label="Product Design",
    tagline="End-to-end product thinking and craft",
    accent="#FF7C9C",
    include=(
        Term(r"product designer", 1.0, "Product Designer"),
        Term(r"product design", 0.95, "product design"),
        Term(r"design thinking", 0.6, "design thinking"),
        Term(r"end[- ]to[- ]end design", 0.6, "end-to-end design"),
        Term(r"user journey", 0.5, "user journeys"),
        Term(r"information architecture", 0.5, "information architecture"),
        Term(r"service design", 0.5, "service design"),
        Term(r"design strateg\w*", 0.5, "design strategy"),
        Term(r"\b0\s?(to|-|→)\s?1\b|zero to one", 0.35, "0→1 product"),
        Term(r"\bfigma\b", 0.5, "Figma"),
        Term(r"\bprototyp\w*", 0.4, "prototyping"),
        Term(r"user research", 0.5, "user research"),
        Term(r"design critique", 0.35, "design critique"),
        Term(r"\bportfolio\b", 0.3, "portfolio"),
    ),
    exclude=(
        r"product manager",
        r"product marketing",
        r"\bmechanical\b",
        r"\bindustrial design(er)?\b",
        r"\bcad\b",
        r"solidworks",
    ),
    anchors=(r"\bdesign(er)?\b",),
    saturation=4.0,
    keywords_for_search=("product designer", "product design internship"),
)

# Optional, off by default — from the second sketch page (DRDO / ISRO / research).
GOVT_RESEARCH = InterestProfile(
    slug="govt_research",
    label="Govt & Research",
    tagline="DRDO, ISRO, national labs and research internships",
    accent="#F5C451",
    include=(
        Term(r"\bdrdo\b", 1.0, "DRDO"),
        Term(r"\bisro\b", 1.0, "ISRO"),
        Term(r"\bbarc\b", 0.8, "BARC"),
        Term(r"\bcsir\b", 0.8, "CSIR"),
        Term(r"\bdst\b", 0.5, "DST"),
        Term(r"research intern(ship)?", 0.8, "research internship"),
        Term(r"research (assistant|associate|fellow)", 0.7, "research role"),
        Term(r"\bjrf\b|junior research fellow", 0.7, "JRF"),
        Term(r"national (laboratory|institute)", 0.5, "national lab"),
        Term(r"\biit\b|\biiit\b|\bnit\b", 0.4, "IIT/IIIT/NIT"),
    ),
    anchors=(r"\bdrdo\b", r"\bisro\b", r"\bbarc\b", r"\bcsir\b", r"research"),
    saturation=3.0,
    keywords_for_search=("drdo internship", "isro internship", "research internship"),
)

ALL_PROFILES: tuple[InterestProfile, ...] = (
    FLUTTER,
    UI_UX,
    PRODUCT_DESIGN,
    GOVT_RESEARCH,
)

DEFAULT_PROFILE_SLUGS: tuple[str, ...] = ("flutter", "ui_ux", "product_design")

PROFILES_BY_SLUG: dict[str, InterestProfile] = {p.slug: p for p in ALL_PROFILES}


def get_profiles(slugs: list[str] | tuple[str, ...] | None = None) -> list[InterestProfile]:
    """Resolve slugs to profiles, silently dropping unknown ones."""
    if not slugs:
        return [PROFILES_BY_SLUG[s] for s in DEFAULT_PROFILE_SLUGS]
    return [PROFILES_BY_SLUG[s] for s in slugs if s in PROFILES_BY_SLUG]


# --- compiled caches -------------------------------------------------------

_COMPILED: dict[str, re.Pattern[str]] = {}


def compiled(pattern: str) -> re.Pattern[str]:
    regex = _COMPILED.get(pattern)
    if regex is None:
        regex = re.compile(pattern, re.IGNORECASE)
        _COMPILED[pattern] = regex
    return regex
