"""Parser tests for every source, run against recorded response fixtures.

Network calls are never made here — each scraper's `parse()` is the unit under
test, so a source changing its payload shape shows up as a failing test rather
than a silently empty feed.
"""

from __future__ import annotations

import pytest
from conftest import load_json, load_text

from app.scrapers import (
    ArbeitnowScraper,
    GreenhouseScraper,
    HackerNewsHiringScraper,
    HimalayasScraper,
    InternshalaScraper,
    LeverScraper,
    RemoteOKScraper,
    WeWorkRemotelyScraper,
    build_scrapers,
)


class TestRemoteOK:
    @pytest.fixture
    def jobs(self):
        return RemoteOKScraper().parse(load_json("remoteok.json"))

    def test_skips_legal_notice_and_broken_rows(self, jobs):
        assert len(jobs) == 2

    def test_maps_fields(self, jobs):
        job = jobs[0]
        assert job.title == "Senior Flutter Engineer"
        assert job.company_name == "Acme Labs"
        assert job.apply_url == "https://remoteok.com/l/1042871"
        assert job.remote_hint is True
        assert job.salary_raw == "$120,000 - $165,000"
        assert "flutter" in job.tags

    def test_falls_back_to_url_when_apply_url_missing(self, jobs):
        assert jobs[1].apply_url.startswith("https://remoteok.com/remote-jobs/")

    def test_bad_payload_is_empty(self):
        assert RemoteOKScraper().parse({"not": "a list"}) == []
        assert RemoteOKScraper().parse(None) == []


class TestArbeitnow:
    @pytest.fixture
    def jobs(self):
        return ArbeitnowScraper().parse(load_json("arbeitnow.json"))

    def test_parses_all_rows(self, jobs):
        # Filtering by relevance happens later in the pipeline, not in the parser.
        assert len(jobs) == 3

    def test_remote_flag_and_types(self, jobs):
        flutter = next(j for j in jobs if j.title == "Flutter Developer")
        assert flutter.remote_hint is True
        assert flutter.employment_type_raw == "Full Time"

    def test_bad_payload_is_empty(self):
        assert ArbeitnowScraper().parse([]) == []
        assert ArbeitnowScraper().parse({"data": "nope"}) == []


class TestHimalayas:
    @pytest.fixture
    def jobs(self):
        return HimalayasScraper().parse(load_json("himalayas.json"))

    def test_count_and_salary(self, jobs):
        assert len(jobs) == 2
        assert jobs[0].salary_raw == "$95,000 - $130,000"

    def test_location_restrictions_are_joined(self, jobs):
        assert jobs[1].location == "India, Remote"

    def test_missing_salary_is_none(self, jobs):
        assert jobs[1].salary_raw is None


class TestWeWorkRemotely:
    @pytest.fixture
    def jobs(self):
        return WeWorkRemotelyScraper().parse(load_text("weworkremotely.xml"), category="design")

    def test_splits_company_from_title(self, jobs):
        assert jobs[0].company_name == "Lumen Studio"
        assert jobs[0].title == "Senior Product Designer"

    def test_drops_items_without_a_company_prefix(self, jobs):
        assert len(jobs) == 2
        assert all("Malformed" not in j.title for j in jobs)

    def test_region_becomes_location(self, jobs):
        assert jobs[0].location == "Anywhere in the World"

    def test_invalid_xml_is_empty(self):
        assert WeWorkRemotelyScraper().parse("<not xml") == []


class TestGreenhouse:
    @pytest.fixture
    def jobs(self):
        return GreenhouseScraper(boards=[]).parse(load_json("greenhouse.json"), board_slug="figma")

    def test_uses_board_slug_as_company(self, jobs):
        assert jobs[0].company_name == "Figma"

    def test_unescapes_double_encoded_content(self, jobs):
        assert "<strong>design system</strong>" in jobs[0].description_html

    def test_location_and_departments(self, jobs):
        assert jobs[0].location == "San Francisco, CA"
        assert jobs[0].tags == ["Design"]

    def test_source_id_is_namespaced_by_board(self, jobs):
        assert jobs[0].source_id.startswith("figma:")


class TestLever:
    @pytest.fixture
    def jobs(self):
        return LeverScraper(boards=[]).parse(load_json("lever.json"), board_slug="swiggy")

    def test_maps_categories(self, jobs):
        assert jobs[0].location == "Bengaluru, India"
        assert jobs[0].employment_type_raw == "Full-time"
        assert "Consumer Engineering" in jobs[0].tags

    def test_workplace_type_drives_remote_hint(self, jobs):
        assert jobs[0].remote_hint is None  # hybrid
        assert jobs[1].remote_hint is True  # remote

    def test_epoch_millis_preserved_for_later_parsing(self, jobs):
        assert jobs[0].posted_at == 1754800000000


class TestHackerNews:
    @pytest.fixture
    def jobs(self):
        return HackerNewsHiringScraper().parse(load_json("hn_hiring.json"))

    def test_parses_pipe_convention(self, jobs):
        assert len(jobs) == 2
        stellar = jobs[0]
        assert stellar.company_name == "Stellar Systems"
        assert stellar.title == "Senior Flutter Engineer"
        assert stellar.remote_hint is True

    def test_extracts_apply_url_from_body(self, jobs):
        assert jobs[0].apply_url == "https://stellar.example.com/careers/flutter"

    def test_ignores_chatter_and_urls_as_company(self, jobs):
        companies = {j.company_name for j in jobs}
        assert not any(c.startswith("http") for c in companies)
        assert "Does anyone know if this thread is still active?" not in companies


class TestInternshala:
    @pytest.fixture
    def jobs(self):
        return InternshalaScraper().parse(load_text("internshala.html"))

    def test_parses_cards(self, jobs):
        assert len(jobs) == 2
        assert jobs[0].title == "Flutter Development"
        assert jobs[0].company_name == "BrightLabs"

    def test_absolute_urls(self, jobs):
        assert jobs[0].apply_url.startswith("https://internshala.com/internship/detail/")

    def test_work_from_home_is_remote(self, jobs):
        assert jobs[0].remote_hint is True
        assert jobs[1].remote_hint is False

    def test_stipend_captured(self, jobs):
        assert "15,000" in jobs[0].salary_raw

    def test_skips_cards_without_a_title(self, jobs):
        assert all(j.title for j in jobs)


class TestRegistry:
    def test_builds_only_known_names(self):
        built = build_scrapers(["remoteok", "does-not-exist", "lever"])
        assert [s.name for s in built] == ["remoteok", "lever"]

    def test_default_set_is_non_empty(self):
        assert build_scrapers()

    def test_internshala_is_off_by_default(self):
        assert "internshala" not in [s.name for s in build_scrapers()]
