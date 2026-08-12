"""Scoring a posting against the user's interest profiles.

The scorer is deliberately transparent rather than statistical: every point a
job earns is traceable to a term the app can show back to the user ("matched
Flutter, Dart, Firebase"). That matters for a notification product — an alert
you cannot explain is an alert the user turns off.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .interests import (
    GLOBAL_EXCLUDE,
    InterestProfile,
    compiled,
    get_profiles,
)

# How much a hit is worth depending on where it appears.
FIELD_WEIGHTS: dict[str, float] = {
    "title": 3.0,
    "tags": 1.6,
    "description": 1.0,
    "company": 0.4,
}

# Only the top of a description is trusted; boilerplate ("we use Figma company
# wide") drifts to the bottom of long posts.
DESCRIPTION_WINDOW = 2500

# Multiplier applied when a soft negative shows up outside the title.
SOFT_EXCLUDE_PENALTY = 0.45


@dataclass(frozen=True)
class MatchDocument:
    title: str
    company: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()

    @property
    def fields(self) -> dict[str, str]:
        return {
            "title": self.title or "",
            "company": self.company or "",
            "tags": " ".join(self.tags),
            "description": (self.description or "")[:DESCRIPTION_WINDOW],
        }


@dataclass
class MatchResult:
    profile_slug: str
    score: float
    matched_terms: list[str] = field(default_factory=list)

    @property
    def is_match(self) -> bool:
        return self.score > 0.0


def _matches_any(patterns: tuple[str, ...], text: str) -> bool:
    return any(compiled(p).search(text) for p in patterns)


def score_profile(doc: MatchDocument, profile: InterestProfile) -> MatchResult:
    fields = doc.fields
    title = fields["title"]
    body = " \n ".join(fields.values())

    # 1. Hard global negatives — wrong kind of job entirely.
    if _matches_any(GLOBAL_EXCLUDE, title):
        return MatchResult(profile.slug, 0.0)

    # 2. Profile negatives. In the title they disqualify; elsewhere they dampen.
    penalty = 1.0
    if profile.exclude:
        if _matches_any(profile.exclude, title):
            return MatchResult(profile.slug, 0.0)
        if _matches_any(profile.exclude, body):
            penalty = SOFT_EXCLUDE_PENALTY

    # 3. Anchor gate — the posting has to be in the right universe at all.
    if profile.anchors and not _matches_any(profile.anchors, body):
        return MatchResult(profile.slug, 0.0)

    # 4. Weighted term accumulation; each term counts once, at its best field.
    total = 0.0
    matched: list[str] = []
    for term in profile.include:
        regex = compiled(term.pattern)
        best_field_weight = 0.0
        for field_name, text in fields.items():
            if text and regex.search(text):
                best_field_weight = max(best_field_weight, FIELD_WEIGHTS[field_name])
        if best_field_weight:
            total += term.weight * best_field_weight
            matched.append(term.display)

    if not matched:
        return MatchResult(profile.slug, 0.0)

    score = min(1.0, (total * penalty) / profile.saturation)
    return MatchResult(profile.slug, round(score, 4), matched)


def score_all(
    doc: MatchDocument,
    profile_slugs: list[str] | tuple[str, ...] | None = None,
    *,
    threshold: float = 0.0,
) -> list[MatchResult]:
    """Score against every requested profile, best first."""
    results = [score_profile(doc, profile) for profile in get_profiles(profile_slugs)]
    kept = [r for r in results if r.score > threshold]
    kept.sort(key=lambda r: r.score, reverse=True)
    return kept


def best_match(
    doc: MatchDocument, profile_slugs: list[str] | tuple[str, ...] | None = None
) -> MatchResult | None:
    results = score_all(doc, profile_slugs)
    return results[0] if results else None
