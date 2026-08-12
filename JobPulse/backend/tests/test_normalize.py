"""Normalisation of scraped strings."""

from __future__ import annotations

import pytest

from app.normalize import (
    detect_employment_type,
    detect_internship,
    detect_remote,
    detect_seniority,
    fingerprint,
    parse_salary,
    parse_timestamp,
    slugify,
    strip_html,
    truncate,
)


class TestStripHtml:
    def test_flattens_markup_to_text(self):
        html = "<div><p>Hello <strong>world</strong></p><ul><li>One</li><li>Two</li></ul></div>"
        assert strip_html(html) == "Hello world\nOne\nTwo"

    def test_drops_scripts_and_styles(self):
        html = "<p>Keep</p><script>alert('no')</script><style>.a{color:red}</style>"
        assert "alert" not in strip_html(html)
        assert "Keep" in strip_html(html)

    def test_handles_plain_text_and_empty(self):
        assert strip_html("just text") == "just text"
        assert strip_html(None) == ""
        assert strip_html("") == ""


class TestFingerprint:
    def test_is_stable_across_decoration_differences(self):
        a = fingerprint("Google", "Product Designer", "Bengaluru, India")
        b = fingerprint("google", "product  designer", "bengaluru, india")
        assert a == b

    def test_strips_trailing_modality_suffix(self):
        assert fingerprint("Acme", "Flutter Developer - Remote", "Remote") == fingerprint(
            "Acme", "Flutter Developer", "Remote"
        )

    def test_different_roles_differ(self):
        assert fingerprint("Acme", "Flutter Developer") != fingerprint("Acme", "UX Designer")


class TestRemoteDetection:
    @pytest.mark.parametrize(
        "location", ["Remote", "Work from home", "Anywhere in the World", "REMOTE - India"]
    )
    def test_positive(self, location):
        assert detect_remote(location) is True

    def test_hybrid_is_not_remote(self):
        assert detect_remote("Bengaluru (Hybrid)", "hybrid role") is False

    def test_onsite(self):
        assert detect_remote("Bengaluru, India") is False


class TestInternshipDetection:
    @pytest.mark.parametrize(
        "title",
        ["Product Design Intern", "UI/UX Design Internship", "Graduate Trainee", "Design Co-op"],
    )
    def test_positive(self, title):
        assert detect_internship(title) is True

    def test_internal_is_not_internship(self):
        assert detect_internship("Internal Tools Engineer") is False

    def test_international_is_not_internship(self):
        assert detect_internship("International Growth Designer") is False

    def test_reads_top_of_description(self):
        assert detect_internship("Designer", "This is a 12 week internship in our design team.")

    def test_ignores_internship_mentioned_late(self):
        tail = "x" * 600 + " previous internship experience helps"
        assert detect_internship("Senior Designer", tail) is False


class TestSeniority:
    @pytest.mark.parametrize(
        ("title", "expected"),
        [
            ("Flutter Development Intern", "intern"),
            ("Staff Product Designer", "lead"),
            ("Senior UX Designer", "senior"),
            ("Junior Designer", "junior"),
            ("Product Designer", "mid"),
        ],
    )
    def test_levels(self, title, expected):
        assert detect_seniority(title) == expected

    def test_intern_beats_senior_when_both_present(self):
        assert detect_seniority("Senior Design Intern") == "intern"


class TestEmploymentType:
    def test_internship_wins(self):
        assert detect_employment_type("Design Intern", "", "Full-time") == "internship"

    def test_contract(self):
        assert detect_employment_type("UI Designer", "", "Contract") == "contract"

    def test_default_is_full_time(self):
        assert detect_employment_type("UI Designer", "Great team") == "full_time"


class TestSalary:
    def test_usd_range(self):
        low, high, currency, raw = parse_salary("$120,000 - $165,000 per year")
        assert (low, high, currency) == (120000.0, 165000.0, "USD")
        assert raw

    def test_k_notation_applies_to_both_ends(self):
        low, high, currency, _ = parse_salary("$120k - $165k")
        assert (low, high, currency) == (120000.0, 165000.0, "USD")

    def test_inr_lakh_notation(self):
        low, high, currency, _ = parse_salary("₹18L - ₹32L per annum")
        assert (low, high, currency) == (1800000.0, 3200000.0, "INR")

    def test_inr_monthly_stipend(self):
        low, high, currency, _ = parse_salary("₹40,000 - ₹60,000 /month")
        assert (low, high, currency) == (40000.0, 60000.0, "INR")

    def test_reversed_range_is_ordered(self):
        low, high, _, _ = parse_salary("$165,000 - $120,000")
        assert low < high

    def test_single_value(self):
        low, high, currency, _ = parse_salary("Base of $130,000")
        assert (low, high, currency) == (130000.0, None, "USD")

    def test_no_salary(self):
        assert parse_salary("Competitive compensation") == (None, None, None, None)
        assert parse_salary(None) == (None, None, None, None)

    def test_ignores_tiny_numbers(self):
        assert parse_salary("$5 lunch stipend")[0] is None


class TestTimestamps:
    def test_iso(self):
        assert parse_timestamp("2026-08-11T06:00:00+00:00").year == 2026

    def test_zulu(self):
        assert parse_timestamp("2026-08-11T06:00:00Z").tzinfo is not None

    def test_epoch_seconds_and_millis_agree(self):
        assert parse_timestamp(1755000000) == parse_timestamp(1755000000000)

    def test_rfc2822(self):
        assert parse_timestamp("Mon, 11 Aug 2026 09:12:00 +0000").day == 11

    def test_garbage_is_none(self):
        assert parse_timestamp("not a date") is None
        assert parse_timestamp(None) is None
        assert parse_timestamp("") is None

    def test_naive_datetime_gets_utc(self):
        from datetime import datetime

        assert parse_timestamp(datetime(2026, 8, 11)).tzinfo is not None


def test_slugify():
    assert slugify("We Work Remotely!") == "we-work-remotely"
    assert slugify("  ") == "unknown"


def test_truncate():
    assert truncate("short", 10) == "short"
    assert truncate("a" * 20, 10).endswith("…")
    assert len(truncate("a" * 20, 10)) == 10
