"""Feed, job detail, company detail and the interest catalogue."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import selectinload

from ..interests import ALL_PROFILES, DEFAULT_PROFILE_SLUGS
from ..models import Company, Job, JobMatch, utcnow
from ..schemas import (
    CompanyOut,
    CompanyStackOut,
    FeedResponse,
    InterestOut,
    JobDetail,
    StackedFeedResponse,
)
from ..serializers import company_brief, company_out, job_detail, job_summary
from .deps import SessionDep

router = APIRouter(prefix="/v1", tags=["jobs"])

FeedFilter = Literal["all", "popular", "new", "internships", "remote"]

NEW_WINDOW = timedelta(hours=48)
MAX_LIMIT = 100


@router.get("/interests", response_model=list[InterestOut])
def list_interests() -> list[InterestOut]:
    """Catalogue backing the onboarding and profile screens."""
    return [
        InterestOut(slug=p.slug, label=p.label, tagline=p.tagline, accent=p.accent)
        for p in ALL_PROFILES
    ]


def _base_query(
    interests: list[str],
    *,
    min_score: float,
    query: str | None,
    internships_only: bool,
    remote_only: bool,
):
    stmt = (
        select(Job, func.max(JobMatch.score).label("score"))
        .join(JobMatch, JobMatch.job_id == Job.id)
        .where(Job.is_active.is_(True), JobMatch.profile_slug.in_(interests))
        .group_by(Job.id)
        .having(func.max(JobMatch.score) >= min_score)
        .options(selectinload(Job.company), selectinload(Job.matches))
    )
    if internships_only:
        stmt = stmt.where(Job.is_internship.is_(True))
    if remote_only:
        stmt = stmt.where(Job.is_remote.is_(True))
    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Job.title.ilike(pattern),
                Job.company_name.ilike(pattern),
                cast(Job.tags, String).ilike(pattern),
            )
        )
    return stmt


@router.get("/feed", response_model=FeedResponse)
def get_feed(
    session: SessionDep,
    interests: Annotated[list[str] | None, Query()] = None,
    filter: FeedFilter = "all",
    query: Annotated[str | None, Query(max_length=120)] = None,
    min_score: Annotated[float, Query(alias="minScore", ge=0.0, le=1.0)] = 0.35,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 25,
    cursor: Annotated[str | None, Query()] = None,
) -> FeedResponse:
    """The list behind the Home screen's All / Popular / New chips."""
    selected = interests or list(DEFAULT_PROFILE_SLUGS)
    offset = _decode_cursor(cursor)

    stmt = _base_query(
        selected,
        min_score=min_score,
        query=query,
        internships_only=filter == "internships",
        remote_only=filter == "remote",
    )

    if filter == "new":
        stmt = stmt.where(Job.posted_at >= utcnow() - NEW_WINDOW)
        stmt = stmt.order_by(Job.posted_at.desc())
    elif filter == "popular":
        # Best match first, most recent as the tiebreak.
        stmt = stmt.order_by(func.max(JobMatch.score).desc(), Job.posted_at.desc())
    else:
        stmt = stmt.order_by(Job.posted_at.desc(), func.max(JobMatch.score).desc())

    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = session.execute(stmt.offset(offset).limit(limit)).all()

    items = [job_summary(row[0]) for row in rows]
    next_cursor = str(offset + limit) if offset + limit < total else None

    return FeedResponse(items=items, next_cursor=next_cursor, total=total, generated_at=utcnow())


@router.get("/feed/stacked", response_model=StackedFeedResponse)
def get_stacked_feed(
    session: SessionDep,
    interests: Annotated[list[str] | None, Query()] = None,
    min_score: Annotated[float, Query(alias="minScore", ge=0.0, le=1.0)] = 0.35,
    companies: Annotated[int, Query(ge=1, le=40)] = 12,
    per_company: Annotated[int, Query(alias="perCompany", ge=1, le=10)] = 5,
) -> StackedFeedResponse:
    """Feed grouped by company — one stack per employer, newest first.

    Mirrors how iOS groups notifications by `thread-id`, so the collapsed cards
    on the second screen line up with what actually lands on the lock screen.
    """
    selected = interests or list(DEFAULT_PROFILE_SLUGS)
    stmt = (
        _base_query(
            selected, min_score=min_score, query=None, internships_only=False, remote_only=False
        )
        .order_by(Job.posted_at.desc())
        .limit(companies * per_company * 4)
    )

    grouped: dict[str, list[Job]] = defaultdict(list)
    for row in session.execute(stmt).all():
        job = row[0]
        grouped[job.company_name].append(job)

    stacks: list[CompanyStackOut] = []
    for name, jobs in grouped.items():
        jobs.sort(key=lambda j: j.posted_at or utcnow(), reverse=True)
        trimmed = jobs[:per_company]
        summaries = [job_summary(j) for j in trimmed]
        stacks.append(
            CompanyStackOut(
                company=company_brief(trimmed[0].company, name),
                jobs=summaries,
                top_score=max((s.top_score for s in summaries), default=0.0),
                latest_posted_at=trimmed[0].posted_at,
            )
        )

    stacks.sort(key=lambda s: s.latest_posted_at or utcnow(), reverse=True)
    return StackedFeedResponse(stacks=stacks[:companies], generated_at=utcnow())


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(session: SessionDep, job_id: int) -> JobDetail:
    job = session.get(Job, job_id)
    if job is None or not job.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")

    related = list(
        session.scalars(
            select(Job)
            .where(
                Job.company_name == job.company_name,
                Job.id != job.id,
                Job.is_active.is_(True),
            )
            .order_by(Job.posted_at.desc())
            .limit(5)
        )
    )
    return job_detail(job, related)


@router.get("/companies/{slug}", response_model=CompanyOut)
def get_company(session: SessionDep, slug: str) -> CompanyOut:
    company = session.scalar(select(Company).where(Company.slug == slug))
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    return company_out(company)


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(cursor))
    except ValueError:
        return 0
