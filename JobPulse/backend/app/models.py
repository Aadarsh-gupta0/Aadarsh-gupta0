"""SQLAlchemy ORM models."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class DeliveryStatus(enum.StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class SaveState(enum.StrEnum):
    saved = "saved"
    applied = "applied"
    dismissed = "dismissed"


class Company(Base):
    """Company profile backing the detail screen's 'Comp Desc / Stats / Links' blocks."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    website: Mapped[str | None] = mapped_column(String(500))
    careers_url: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    industry: Mapped[str | None] = mapped_column(String(140))
    headquarters: Mapped[str | None] = mapped_column(String(200))
    employee_count: Mapped[str | None] = mapped_column(String(60))
    founded_year: Mapped[int | None] = mapped_column(Integer)
    open_roles: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    jobs: Mapped[list[Job]] = relationship(back_populates="company", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_posted_at", "posted_at"),
        Index("ix_jobs_source_sourceid", "source", "source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Stable content hash — the dedupe key across every source.
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    source: Mapped[str] = mapped_column(String(60), index=True)
    source_id: Mapped[str] = mapped_column(String(200))

    title: Mapped[str] = mapped_column(String(320))
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    company_name: Mapped[str] = mapped_column(String(200), index=True)

    location: Mapped[str | None] = mapped_column(String(240))
    is_remote: Mapped[bool] = mapped_column(Boolean, default=False)
    country: Mapped[str | None] = mapped_column(String(80))

    employment_type: Mapped[str | None] = mapped_column(String(60))  # full_time / internship / ...
    is_internship: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    seniority: Mapped[str | None] = mapped_column(String(40))  # intern/junior/mid/senior/lead

    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    salary_currency: Mapped[str | None] = mapped_column(String(8))
    salary_raw: Mapped[str | None] = mapped_column(String(200))

    description_text: Mapped[str] = mapped_column(Text, default="")
    description_html: Mapped[str | None] = mapped_column(Text)
    apply_url: Mapped[str] = mapped_column(String(1000))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped[Company | None] = relationship(back_populates="jobs")
    matches: Mapped[list[JobMatch]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    @property
    def top_score(self) -> float:
        return max((m.score for m in self.matches), default=0.0)


class JobMatch(Base):
    """Score of one job against one interest profile (flutter / ui_ux / product_design ...)."""

    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("job_id", "profile_slug", name="uq_job_profile"),
        Index("ix_job_matches_profile_score", "profile_slug", "score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    profile_slug: Mapped[str] = mapped_column(String(60), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    matched_terms: Mapped[list[str]] = mapped_column(JSON, default=list)

    job: Mapped[Job] = relationship(back_populates="matches")


class Device(Base):
    """One installed copy of the iOS app, addressed by its APNs device token."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    apns_token: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    install_id: Mapped[str | None] = mapped_column(String(80), index=True)

    display_name: Mapped[str | None] = mapped_column(String(80))
    interests: Mapped[list[str]] = mapped_column(JSON, default=list)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    internships_only: Mapped[bool] = mapped_column(Boolean, default=False)
    min_score: Mapped[float] = mapped_column(Float, default=0.55)
    timezone: Mapped[str] = mapped_column(String(60), default="Asia/Kolkata")
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    app_version: Mapped[str | None] = mapped_column(String(30))
    environment: Mapped[str] = mapped_column(String(20), default="sandbox")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    deliveries: Mapped[list[Delivery]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class Delivery(Base):
    """Notification ledger — the reason a job is never pushed to the same device twice."""

    __tablename__ = "deliveries"
    __table_args__ = (UniqueConstraint("device_id", "job_id", name="uq_device_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, native_enum=False), default=DeliveryStatus.pending
    )
    score: Mapped[float] = mapped_column(Float, default=0.0)
    apns_id: Mapped[str | None] = mapped_column(String(80))
    error: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device: Mapped[Device] = relationship(back_populates="deliveries")


class SavedJob(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (UniqueConstraint("device_id", "job_id", name="uq_saved_device_job"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    state: Mapped[SaveState] = mapped_column(
        Enum(SaveState, native_enum=False), default=SaveState.saved
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ScrapeRun(Base):
    """One pass of one scraper — useful for spotting a source that silently broke."""

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(60), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    found: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[int] = mapped_column(Integer, default=0)
    matched: Mapped[int] = mapped_column(Integer, default=0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    error: Mapped[str | None] = mapped_column(String(500))
