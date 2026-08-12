"""Scrape → normalise → dedupe → score → store → notify."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import session_scope
from .interests import ALL_PROFILES
from .matching import MatchDocument, MatchResult, score_all
from .models import Company, Delivery, DeliveryStatus, Device, Job, JobMatch, ScrapeRun, utcnow
from .normalize import (
    clean_text,
    detect_country,
    detect_employment_type,
    detect_internship,
    detect_remote,
    detect_seniority,
    fingerprint,
    parse_salary,
    parse_timestamp,
    slugify,
    strip_html,
)
from .push import APNsClient, build_payload, collapse_id_for
from .scrapers import PoliteClient, RawJob, Scraper, build_scrapers

log = logging.getLogger(__name__)

ALL_PROFILE_SLUGS = tuple(p.slug for p in ALL_PROFILES)


@dataclass
class SourceReport:
    source: str
    found: int = 0
    created: int = 0
    matched: int = 0
    ok: bool = True
    error: str | None = None


@dataclass
class IngestReport:
    sources: list[SourceReport] = field(default_factory=list)
    notifications_sent: int = 0
    started_at: datetime = field(default_factory=utcnow)
    finished_at: datetime | None = None

    @property
    def total_found(self) -> int:
        return sum(s.found for s in self.sources)

    @property
    def total_created(self) -> int:
        return sum(s.created for s in self.sources)

    @property
    def total_matched(self) -> int:
        return sum(s.matched for s in self.sources)

    def as_dict(self) -> dict:
        return {
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "found": self.total_found,
            "created": self.total_created,
            "matched": self.total_matched,
            "notifications_sent": self.notifications_sent,
            "sources": [
                {
                    "source": s.source,
                    "found": s.found,
                    "created": s.created,
                    "matched": s.matched,
                    "ok": s.ok,
                    "error": s.error,
                }
                for s in self.sources
            ],
        }


# --- normalisation ---------------------------------------------------------


@dataclass
class JobDraft:
    fingerprint: str
    source: str
    source_id: str
    title: str
    company_name: str
    company_slug: str
    company_logo_url: str | None
    company_website: str | None
    apply_url: str
    location: str | None
    country: str | None
    is_remote: bool
    employment_type: str
    is_internship: bool
    seniority: str
    salary_min: float | None
    salary_max: float | None
    salary_currency: str | None
    salary_raw: str | None
    description_text: str
    description_html: str | None
    tags: list[str]
    posted_at: datetime | None

    @property
    def document(self) -> MatchDocument:
        return MatchDocument(
            title=self.title,
            company=self.company_name,
            description=self.description_text,
            tags=tuple(self.tags),
        )


def normalize_raw(raw: RawJob) -> JobDraft | None:
    """RawJob → JobDraft, or None when the posting is unusable."""
    if not raw.is_usable():
        return None

    title = clean_text(raw.title)
    company_name = clean_text(raw.company_name)
    if not title or not company_name:
        return None

    description_text = clean_text(raw.description_text or "") or strip_html(raw.description_html)
    location = clean_text(raw.location or "") or None

    is_remote = (
        bool(raw.remote_hint)
        if raw.remote_hint is not None
        else detect_remote(location, title, description_text[:500])
    )

    employment_type = detect_employment_type(title, description_text, raw.employment_type_raw)
    is_internship = detect_internship(title, description_text, raw.employment_type_raw)
    if is_internship:
        employment_type = "internship"

    salary_source = raw.salary_raw or description_text
    salary_min, salary_max, currency, salary_raw = parse_salary(salary_source)

    tags = sorted({clean_text(str(t)).lower() for t in raw.tags if t})[:24]

    return JobDraft(
        fingerprint=fingerprint(company_name, title, location),
        source=raw.source,
        source_id=str(raw.source_id),
        title=title[:320],
        company_name=company_name[:200],
        company_slug=slugify(company_name),
        company_logo_url=raw.company_logo_url,
        company_website=raw.company_website,
        apply_url=raw.apply_url[:1000],
        location=location[:240] if location else None,
        country=detect_country(location),
        is_remote=is_remote,
        employment_type=employment_type,
        is_internship=is_internship,
        seniority=detect_seniority(title, description_text),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=currency,
        salary_raw=(raw.salary_raw or salary_raw or None),
        description_text=description_text[:20000],
        description_html=(raw.description_html or None),
        tags=tags,
        posted_at=parse_timestamp(raw.posted_at),
    )


# --- persistence -----------------------------------------------------------


def _upsert_company(session: Session, draft: JobDraft) -> Company:
    company = session.scalar(select(Company).where(Company.slug == draft.company_slug))
    if company is None:
        company = Company(slug=draft.company_slug, name=draft.company_name)
        session.add(company)
        session.flush()
    # Only fill blanks — never overwrite good data with a source that has less.
    if draft.company_logo_url and not company.logo_url:
        company.logo_url = draft.company_logo_url
    if draft.company_website and not company.website:
        company.website = draft.company_website
        company.careers_url = company.careers_url or draft.company_website
    return company


def persist_draft(
    session: Session, draft: JobDraft, matches: list[MatchResult]
) -> tuple[Job | None, bool]:
    """Insert or refresh a job. Returns `(job, created)`."""
    existing = session.scalar(select(Job).where(Job.fingerprint == draft.fingerprint))
    company = _upsert_company(session, draft)

    if existing is not None:
        existing.is_active = True
        # A richer description from a second source is an upgrade worth taking.
        if len(draft.description_text) > len(existing.description_text or ""):
            existing.description_text = draft.description_text
            existing.description_html = draft.description_html or existing.description_html
        if draft.salary_raw and not existing.salary_raw:
            existing.salary_raw = draft.salary_raw
            existing.salary_min = draft.salary_min
            existing.salary_max = draft.salary_max
            existing.salary_currency = draft.salary_currency
        if draft.posted_at and not existing.posted_at:
            existing.posted_at = draft.posted_at
        return existing, False

    job = Job(
        fingerprint=draft.fingerprint,
        source=draft.source,
        source_id=draft.source_id,
        title=draft.title,
        company_id=company.id,
        company_name=draft.company_name,
        location=draft.location,
        country=draft.country,
        is_remote=draft.is_remote,
        employment_type=draft.employment_type,
        is_internship=draft.is_internship,
        seniority=draft.seniority,
        salary_min=draft.salary_min,
        salary_max=draft.salary_max,
        salary_currency=draft.salary_currency,
        salary_raw=draft.salary_raw,
        description_text=draft.description_text,
        description_html=draft.description_html,
        apply_url=draft.apply_url,
        tags=draft.tags,
        posted_at=draft.posted_at or utcnow(),
    )
    session.add(job)
    session.flush()

    for match in matches:
        session.add(
            JobMatch(
                job_id=job.id,
                profile_slug=match.profile_slug,
                score=match.score,
                matched_terms=match.matched_terms,
            )
        )
    company.open_roles = (company.open_roles or 0) + 1
    return job, True


# --- ingestion -------------------------------------------------------------


async def ingest_source(scraper: Scraper, client: PoliteClient, settings: Settings) -> SourceReport:
    report = SourceReport(source=scraper.name)
    run = ScrapeRun(source=scraper.name)

    with session_scope() as session:
        session.add(run)
        session.flush()
        run_id = run.id

    try:
        raw_jobs = await scraper.fetch(client)
    except Exception as exc:  # a single bad source must not stop the pass
        log.exception("Scraper %s failed", scraper.name)
        report.ok = False
        report.error = f"{type(exc).__name__}: {exc}"[:500]
        _finish_run(run_id, report)
        return report

    report.found = len(raw_jobs)

    with session_scope() as session:
        for raw in raw_jobs:
            draft = normalize_raw(raw)
            if draft is None:
                continue
            matches = score_all(
                draft.document, ALL_PROFILE_SLUGS, threshold=settings.match_threshold
            )
            if not matches:
                continue
            _job, created = persist_draft(session, draft, matches)
            report.matched += 1
            if created:
                report.created += 1

    _finish_run(run_id, report)
    return report


def _finish_run(run_id: int, report: SourceReport) -> None:
    with session_scope() as session:
        run = session.get(ScrapeRun, run_id)
        if run is None:
            return
        run.finished_at = utcnow()
        run.found = report.found
        run.created = report.created
        run.matched = report.matched
        run.ok = report.ok
        run.error = report.error


async def run_ingest(
    scrapers: list[Scraper] | None = None,
    *,
    settings: Settings | None = None,
    notify: bool = True,
) -> IngestReport:
    settings = settings or get_settings()
    scrapers = scrapers if scrapers is not None else build_scrapers()
    report = IngestReport()

    async with PoliteClient(settings) as client:
        # Sources are independent; the per-host pacing inside PoliteClient keeps
        # concurrency from turning into hammering.
        results = await asyncio.gather(
            *(ingest_source(scraper, client, settings) for scraper in scrapers),
            return_exceptions=True,
        )

    for scraper, result in zip(scrapers, results, strict=True):
        if isinstance(result, BaseException):
            report.sources.append(
                SourceReport(
                    source=scraper.name,
                    ok=False,
                    error=f"{type(result).__name__}: {result}"[:500],
                )
            )
        else:
            report.sources.append(result)

    if notify:
        report.notifications_sent = await dispatch_notifications(settings=settings)

    report.finished_at = utcnow()
    log.info(
        "Ingest done: %s found / %s new / %s matched / %s pushed",
        report.total_found,
        report.total_created,
        report.total_matched,
        report.notifications_sent,
    )
    return report


# --- notification ----------------------------------------------------------


def in_quiet_hours(device: Device, settings: Settings, now: datetime | None = None) -> bool:
    if not device.quiet_hours_enabled:
        return False
    try:
        tz = ZoneInfo(device.timezone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("UTC")
    local_hour = (now or datetime.now(UTC)).astimezone(tz).hour
    start, end = settings.quiet_hours_start, settings.quiet_hours_end
    if start == end:
        return False
    if start < end:
        return start <= local_hour < end
    return local_hour >= start or local_hour < end  # window wraps midnight


def candidate_jobs(
    session: Session, device: Device, settings: Settings, limit: int
) -> list[tuple[Job, JobMatch]]:
    """Highest-scoring jobs this device has not been told about yet."""
    interests = device.interests or list(ALL_PROFILE_SLUGS)
    already_sent = select(Delivery.job_id).where(Delivery.device_id == device.id)
    cutoff = utcnow() - timedelta(days=21)

    stmt = (
        select(Job, JobMatch)
        .join(JobMatch, JobMatch.job_id == Job.id)
        .where(
            Job.is_active.is_(True),
            Job.ingested_at >= cutoff,
            JobMatch.profile_slug.in_(interests),
            JobMatch.score >= max(device.min_score, settings.notify_threshold),
            Job.id.not_in(already_sent),
        )
        .order_by(JobMatch.score.desc(), Job.posted_at.desc())
        .limit(limit * 4)  # over-fetch: one job can match several profiles
    )

    seen: set[int] = set()
    picked: list[tuple[Job, JobMatch]] = []
    for job, match in session.execute(stmt):
        if device.internships_only and not job.is_internship:
            continue
        if job.id in seen:
            continue
        seen.add(job.id)
        picked.append((job, match))
        if len(picked) >= limit:
            break
    return picked


async def dispatch_notifications(
    *, settings: Settings | None = None, apns: APNsClient | None = None
) -> int:
    settings = settings or get_settings()
    owns_client = apns is None
    client = apns or APNsClient(settings)

    sent = 0
    try:
        with session_scope() as session:
            devices = list(
                session.scalars(
                    select(Device).where(Device.is_active.is_(True), Device.push_enabled.is_(True))
                )
            )

            for device in devices:
                if in_quiet_hours(device, settings):
                    log.debug("Device %s is in quiet hours — skipping", device.id)
                    continue

                picks = candidate_jobs(
                    session, device, settings, settings.max_pushes_per_device_per_run
                )
                if not picks:
                    continue

                badge = (
                    session.scalar(
                        select(func.count(Delivery.id)).where(
                            Delivery.device_id == device.id,
                            Delivery.status == DeliveryStatus.sent,
                            Delivery.created_at >= utcnow() - timedelta(days=1),
                        )
                    )
                    or 0
                )

                for index, (job, match) in enumerate(picks, start=1):
                    delivery = Delivery(
                        device_id=device.id,
                        job_id=job.id,
                        score=match.score,
                        status=DeliveryStatus.pending,
                    )
                    session.add(delivery)
                    session.flush()

                    payload = build_payload(
                        job,
                        profile_slug=match.profile_slug,
                        score=match.score,
                        matched_terms=list(match.matched_terms or []),
                        badge=badge + index,
                    )
                    result = await client.send(
                        device.apns_token, payload, collapse_id=collapse_id_for(job)
                    )

                    if result.ok:
                        delivery.status = DeliveryStatus.sent
                        delivery.sent_at = utcnow()
                        delivery.apns_id = result.apns_id
                        sent += 1
                    else:
                        delivery.status = (
                            DeliveryStatus.skipped
                            if result.reason == "NotConfigured"
                            else DeliveryStatus.failed
                        )
                        delivery.error = result.reason
                        if result.token_is_dead:
                            device.is_active = False
                            log.info("Retiring dead device token %s", device.id)
                            break
    finally:
        if owns_client:
            await client.aclose()

    return sent
