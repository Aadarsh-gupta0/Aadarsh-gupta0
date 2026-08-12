"""Ingest, dedupe and notification dispatch."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.db import session_scope
from app.matching import score_all
from app.models import Company, Delivery, DeliveryStatus, Device, Job, JobMatch
from app.pipeline import (
    ALL_PROFILE_SLUGS,
    candidate_jobs,
    dispatch_notifications,
    in_quiet_hours,
    normalize_raw,
    persist_draft,
    run_ingest,
)
from app.push.apns import PushResult
from app.scrapers.base import RawJob, Scraper


def raw(
    title: str = "Flutter Developer",
    company: str = "Acme",
    *,
    source: str = "test",
    source_id: str = "1",
    description: str = "Flutter and Dart across iOS and Android.",
    location: str | None = "Bengaluru, India",
    **kwargs,
) -> RawJob:
    return RawJob(
        source=source,
        source_id=source_id,
        title=title,
        company_name=company,
        apply_url=f"https://example.com/{source_id}",
        description_text=description,
        location=location,
        **kwargs,
    )


def store(job: RawJob) -> Job:
    draft = normalize_raw(job)
    assert draft is not None
    with session_scope() as session:
        matches = score_all(draft.document, ALL_PROFILE_SLUGS, threshold=0.0)
        stored, _created = persist_draft(session, draft, matches)
        session.flush()
        return stored


class TestNormalizeRaw:
    def test_rejects_unusable(self):
        assert (
            normalize_raw(
                RawJob(source="t", source_id="1", title="", company_name="", apply_url="")
            )
            is None
        )

    def test_derives_role_shape(self):
        draft = normalize_raw(
            raw("Product Design Intern", "Google", description="A 12 week internship.")
        )
        assert draft.is_internship is True
        assert draft.employment_type == "internship"
        assert draft.seniority == "intern"

    def test_parses_salary_from_raw_field(self):
        draft = normalize_raw(raw(salary_raw="₹18L - ₹32L"))
        assert draft.salary_min == 1_800_000
        assert draft.salary_currency == "INR"

    def test_remote_hint_overrides_inference(self):
        draft = normalize_raw(raw(location="Bengaluru, India", remote_hint=True))
        assert draft.is_remote is True

    def test_country_detection(self):
        assert normalize_raw(raw(location="Bengaluru, India")).country == "IN"

    def test_html_description_is_flattened(self):
        job = raw(description="")
        job.description_html = "<p>We use <b>Flutter</b></p>"
        draft = normalize_raw(job)
        assert draft.description_text == "We use Flutter"


class TestPersistAndDedupe:
    def test_same_posting_from_two_sources_stores_once(self):
        store(raw(source="a", source_id="1"))
        store(raw(source="b", source_id="2"))
        with session_scope() as session:
            assert session.scalar(select(Job).where(Job.title == "Flutter Developer")) is not None
            assert len(list(session.scalars(select(Job)))) == 1

    def test_second_sighting_reports_not_created(self):
        draft = normalize_raw(raw())
        with session_scope() as session:
            _job, first = persist_draft(session, draft, [])
            _job, second = persist_draft(session, draft, [])
        assert first is True
        assert second is False

    def test_richer_description_replaces_thinner_one(self):
        store(raw(source="a", source_id="1", description="Flutter."))
        long_text = "Flutter and Dart. " * 20
        store(raw(source="b", source_id="2", description=long_text))
        with session_scope() as session:
            job = session.scalar(select(Job))
            assert len(job.description_text) > 100

    def test_company_is_reused_across_jobs(self):
        store(raw("Flutter Developer", "Google", source_id="1"))
        store(
            raw(
                "Product Designer",
                "Google",
                source_id="2",
                description="End-to-end product design in Figma.",
            )
        )
        with session_scope() as session:
            companies = list(session.scalars(select(Company)))
            assert len(companies) == 1
            assert companies[0].open_roles == 2

    def test_matches_are_persisted(self):
        job = store(raw())
        with session_scope() as session:
            matches = list(session.scalars(select(JobMatch).where(JobMatch.job_id == job.id)))
            assert any(m.profile_slug == "flutter" and m.score > 0 for m in matches)
            assert any("Flutter" in (m.matched_terms or []) for m in matches)


class TestQuietHours:
    @pytest.fixture
    def device(self):
        return Device(apns_token="t" * 64, timezone="Asia/Kolkata", quiet_hours_enabled=True)

    def test_inside_window(self, device):
        # 23:00 IST == 17:30 UTC
        assert in_quiet_hours(device, get_settings(), datetime(2026, 8, 12, 17, 30, tzinfo=UTC))

    def test_outside_window(self, device):
        # 12:00 IST == 06:30 UTC
        assert not in_quiet_hours(device, get_settings(), datetime(2026, 8, 12, 6, 30, tzinfo=UTC))

    def test_disabled_flag_wins(self, device):
        device.quiet_hours_enabled = False
        assert not in_quiet_hours(device, get_settings(), datetime(2026, 8, 12, 17, 30, tzinfo=UTC))

    def test_unknown_timezone_falls_back_to_utc(self, device):
        device.timezone = "Mars/Olympus"
        assert in_quiet_hours(device, get_settings(), datetime(2026, 8, 12, 23, 0, tzinfo=UTC))


def make_device(**kwargs) -> Device:
    defaults = {
        "apns_token": "a" * 64,
        "interests": ["flutter", "ui_ux", "product_design"],
        "push_enabled": True,
        "min_score": 0.5,
        "quiet_hours_enabled": False,
        "timezone": "UTC",
    }
    defaults.update(kwargs)
    device = Device(**defaults)
    with session_scope() as session:
        session.add(device)
        session.flush()
        session.expunge(device)
    return device


class TestCandidateSelection:
    def test_picks_matching_jobs(self):
        store(raw("Senior Flutter Engineer"))
        device = make_device()
        with session_scope() as session:
            device = session.merge(device)
            picks = candidate_jobs(session, device, get_settings(), 10)
        assert [job.title for job, _ in picks] == ["Senior Flutter Engineer"]

    def test_respects_interest_selection(self):
        store(raw("Senior Flutter Engineer"))
        device = make_device(interests=["product_design"])
        with session_scope() as session:
            device = session.merge(device)
            assert candidate_jobs(session, device, get_settings(), 10) == []

    def test_internships_only_filter(self):
        store(raw("Senior Flutter Engineer", source_id="1"))
        store(
            raw(
                "Flutter Developer Intern",
                source_id="2",
                description="A 6 month internship with Flutter and Dart.",
            )
        )
        device = make_device(internships_only=True)
        with session_scope() as session:
            device = session.merge(device)
            picks = candidate_jobs(session, device, get_settings(), 10)
        assert all(job.is_internship for job, _ in picks)
        assert picks

    def test_already_delivered_jobs_are_excluded(self):
        job = store(raw("Senior Flutter Engineer"))
        device = make_device()
        with session_scope() as session:
            session.add(Delivery(device_id=device.id, job_id=job.id, status=DeliveryStatus.sent))
        with session_scope() as session:
            device = session.merge(device)
            assert candidate_jobs(session, device, get_settings(), 10) == []

    def test_a_job_matching_two_profiles_appears_once(self):
        store(
            raw(
                "Product Designer (UI/UX)",
                description="Figma, wireframes, user journeys and design systems.",
            )
        )
        device = make_device()
        with session_scope() as session:
            device = session.merge(device)
            picks = candidate_jobs(session, device, get_settings(), 10)
        assert len(picks) == 1

    def test_limit_is_honoured(self):
        for i in range(6):
            store(raw(f"Flutter Engineer {i}", source_id=str(i)))
        device = make_device()
        with session_scope() as session:
            device = session.merge(device)
            assert len(candidate_jobs(session, device, get_settings(), 3)) == 3


class FakeAPNs:
    """Stand-in for APNsClient that records what would have been sent."""

    def __init__(self, result: PushResult | None = None) -> None:
        self.sent: list[tuple[str, dict]] = []
        self.result = result or PushResult(ok=True, status_code=200, apns_id="fake-id")

    @property
    def configured(self) -> bool:
        return True

    async def send(self, token: str, payload: dict, **_kwargs) -> PushResult:
        self.sent.append((token, payload))
        return self.result

    async def aclose(self) -> None:
        return None


class TestDispatch:
    async def test_sends_and_records(self):
        store(raw("Senior Flutter Engineer"))
        make_device()
        apns = FakeAPNs()

        sent = await dispatch_notifications(apns=apns)

        assert sent == 1
        assert len(apns.sent) == 1
        with session_scope() as session:
            delivery = session.scalar(select(Delivery))
            assert delivery.status == DeliveryStatus.sent
            assert delivery.apns_id == "fake-id"

    async def test_never_notifies_twice_for_the_same_job(self):
        store(raw("Senior Flutter Engineer"))
        make_device()
        apns = FakeAPNs()

        first = await dispatch_notifications(apns=apns)
        second = await dispatch_notifications(apns=apns)

        assert (first, second) == (1, 0)
        assert len(apns.sent) == 1

    async def test_payload_groups_by_company(self):
        store(raw("Flutter Engineer", "Google", source_id="1"))
        store(raw("Flutter Architect", "Google", source_id="2"))
        make_device()
        apns = FakeAPNs()

        await dispatch_notifications(apns=apns)

        threads = {payload["aps"]["thread-id"] for _token, payload in apns.sent}
        assert threads == {"company-google"}

    async def test_push_disabled_device_is_skipped(self):
        store(raw("Senior Flutter Engineer"))
        make_device(push_enabled=False)
        apns = FakeAPNs()
        assert await dispatch_notifications(apns=apns) == 0

    async def test_quiet_hours_block_delivery(self):
        store(raw("Senior Flutter Engineer"))
        make_device(quiet_hours_enabled=True, timezone="UTC")
        apns = FakeAPNs()

        settings = get_settings()
        hour = datetime.now(UTC).hour
        # Only assert when "now" genuinely falls inside the configured window.
        if settings.quiet_hours_start <= hour or hour < settings.quiet_hours_end:
            assert await dispatch_notifications(apns=apns) == 0

    async def test_dead_token_retires_the_device(self):
        store(raw("Senior Flutter Engineer"))
        device = make_device()
        apns = FakeAPNs(PushResult(ok=False, status_code=410, reason="Unregistered"))

        await dispatch_notifications(apns=apns)

        with session_scope() as session:
            refreshed = session.get(Device, device.id)
            assert refreshed.is_active is False

    async def test_cap_limits_pushes_per_run(self):
        for i in range(10):
            store(raw(f"Flutter Engineer {i}", source_id=str(i)))
        make_device()
        apns = FakeAPNs()

        sent = await dispatch_notifications(apns=apns)

        assert sent == get_settings().max_pushes_per_device_per_run


class StubScraper(Scraper):
    name = "stub"
    display_name = "Stub"

    def __init__(self, jobs: list[RawJob]) -> None:
        self.jobs = jobs

    async def fetch(self, _client):
        return self.jobs


class ExplodingScraper(Scraper):
    name = "exploding"
    display_name = "Exploding"

    async def fetch(self, _client):
        raise RuntimeError("source is down")


class TestRunIngest:
    async def test_stores_matches_and_reports(self):
        report = await run_ingest(
            [
                StubScraper(
                    [
                        raw("Flutter Developer", source_id="1"),
                        raw(
                            "Dental Hygienist",
                            "Teeth Ltd",
                            source_id="2",
                            description="Clean teeth and assist the dentist.",
                        ),
                    ]
                )
            ],
            notify=False,
        )
        assert report.total_found == 2
        assert report.total_matched == 1  # the dental role is filtered out
        assert report.total_created == 1

    async def test_a_failing_source_does_not_stop_the_pass(self):
        report = await run_ingest(
            [ExplodingScraper(), StubScraper([raw("Flutter Developer")])],
            notify=False,
        )
        by_source = {s.source: s for s in report.sources}
        assert by_source["exploding"].ok is False
        assert "source is down" in by_source["exploding"].error
        assert by_source["stub"].created == 1

    async def test_second_pass_creates_nothing_new(self):
        jobs = [raw("Flutter Developer")]
        await run_ingest([StubScraper(jobs)], notify=False)
        report = await run_ingest([StubScraper(jobs)], notify=False)
        assert report.total_created == 0
        assert report.total_matched == 1

    async def test_report_serialises(self):
        report = await run_ingest([StubScraper([raw()])], notify=False)
        data = report.as_dict()
        assert data["found"] == 1
        assert data["sources"][0]["source"] == "stub"

    async def test_old_jobs_are_not_candidates(self):
        job = store(raw("Senior Flutter Engineer"))
        with session_scope() as session:
            stale = session.get(Job, job.id)
            stale.ingested_at = datetime.now(UTC) - timedelta(days=40)
        device = make_device()
        with session_scope() as session:
            device = session.merge(device)
            assert candidate_jobs(session, device, get_settings(), 10) == []
