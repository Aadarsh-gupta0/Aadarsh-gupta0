"""Interest scoring — the part that decides whether a phone buzzes."""

from __future__ import annotations

import pytest

from app.interests import FLUTTER, GOVT_RESEARCH, PRODUCT_DESIGN, UI_UX
from app.matching import MatchDocument, best_match, score_all, score_profile


def doc(title: str, *, company: str = "Acme", description: str = "", tags=()) -> MatchDocument:
    return MatchDocument(title=title, company=company, description=description, tags=tuple(tags))


class TestFlutter:
    def test_title_match_scores_high(self):
        result = score_profile(doc("Senior Flutter Engineer"), FLUTTER)
        assert result.score >= 0.7
        assert "Flutter" in result.matched_terms

    def test_description_only_scores_lower_than_title(self):
        in_title = score_profile(doc("Flutter Developer"), FLUTTER).score
        in_body = score_profile(
            doc("Software Engineer", description="Our app is written in Flutter and Dart."),
            FLUTTER,
        ).score
        assert 0 < in_body < in_title

    def test_tags_contribute(self):
        with_tags = score_profile(doc("Mobile Engineer", tags=["flutter", "dart"]), FLUTTER).score
        without = score_profile(doc("Mobile Engineer"), FLUTTER).score
        assert with_tags > without

    def test_unrelated_role_scores_zero(self):
        assert score_profile(doc("Accountant"), FLUTTER).score == 0.0

    def test_anchor_gate_blocks_loose_matches(self):
        # "Firebase" alone is not enough to call something a Flutter job.
        result = score_profile(doc("Backend Engineer", description="We use Firebase."), FLUTTER)
        assert result.score == 0.0


class TestUiUx:
    @pytest.mark.parametrize(
        "title", ["UI/UX Designer", "UX Designer", "UI Designer", "Interaction Designer"]
    )
    def test_titles(self, title):
        assert score_profile(doc(title), UI_UX).score >= 0.4

    def test_product_manager_is_excluded(self):
        result = score_profile(
            doc("Product Manager", description="Work with Figma and our design system daily."),
            UI_UX,
        )
        assert result.score == 0.0

    def test_figma_in_a_design_role_counts(self):
        result = score_profile(
            doc("Design Intern", description="You will prototype in Figma and run user research."),
            UI_UX,
        )
        assert result.score > 0.3


class TestProductDesign:
    def test_exact_title(self):
        result = score_profile(doc("Product Designer"), PRODUCT_DESIGN)
        assert result.score >= 0.7

    def test_product_manager_excluded_even_with_design_words(self):
        assert (
            score_profile(
                doc("Product Manager", description="You will drive product design decisions."),
                PRODUCT_DESIGN,
            ).score
            == 0.0
        )

    def test_industrial_design_excluded(self):
        assert score_profile(doc("Industrial Designer"), PRODUCT_DESIGN).score == 0.0

    def test_soft_negative_dampens_rather_than_kills(self):
        clean = score_profile(
            doc("Product Designer", description="Own end-to-end design and prototyping."),
            PRODUCT_DESIGN,
        ).score
        dampened = score_profile(
            doc(
                "Product Designer",
                description="Own end-to-end design. Partner with your product manager daily.",
            ),
            PRODUCT_DESIGN,
        ).score
        assert 0 < dampened < clean


class TestGlobalExcludes:
    @pytest.mark.parametrize(
        "title", ["Sales Executive", "Technical Recruiter", "Business Development Manager"]
    )
    def test_wrong_job_family_is_dropped(self, title):
        results = score_all(doc(title, description="Figma Flutter design"), threshold=0.0)
        assert results == []


class TestScoreAll:
    def test_results_are_sorted_by_score(self):
        results = score_all(
            doc("Product Designer", description="Figma, prototyping, user research."),
            threshold=0.0,
        )
        assert [r.score for r in results] == sorted((r.score for r in results), reverse=True)

    def test_threshold_filters(self):
        weak = doc("Software Engineer", description="We occasionally use Figma.")
        assert score_all(weak, threshold=0.9) == []

    def test_one_job_can_match_several_profiles(self):
        results = score_all(
            doc("Product Designer (UI/UX)", description="Figma, wireframes, user journeys."),
            threshold=0.1,
        )
        slugs = {r.profile_slug for r in results}
        assert {"ui_ux", "product_design"}.issubset(slugs)

    def test_best_match_picks_the_top(self):
        top = best_match(doc("Flutter Developer", description="Dart, BLoC, Firebase."))
        assert top is not None
        assert top.profile_slug == "flutter"

    def test_best_match_returns_none_for_nonsense(self):
        assert best_match(doc("Dental Hygienist")) is None

    def test_scores_are_bounded(self):
        stuffed = doc(
            "Flutter Dart Mobile Developer",
            description="flutter dart riverpod bloc getx firebase android ios " * 20,
            tags=["flutter", "dart", "android", "ios"],
        )
        for result in score_all(stuffed, threshold=0.0):
            assert 0.0 <= result.score <= 1.0


class TestGovtResearch:
    def test_isro_internship(self):
        result = score_profile(
            doc("Research Intern", company="ISRO", description="Research internship in avionics."),
            GOVT_RESEARCH,
        )
        assert result.score > 0.5

    def test_not_enabled_by_default(self):
        results = score_all(doc("Research Intern", company="ISRO"), threshold=0.0)
        assert all(r.profile_slug != "govt_research" for r in results)
