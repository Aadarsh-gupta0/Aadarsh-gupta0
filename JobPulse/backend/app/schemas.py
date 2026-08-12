"""Pydantic DTOs — the exact JSON the iOS app decodes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# --- interests -------------------------------------------------------------


class InterestOut(CamelModel):
    slug: str
    label: str
    tagline: str
    accent: str


# --- companies -------------------------------------------------------------


class CompanyBrief(CamelModel):
    slug: str
    name: str
    logo_url: str | None = None


class CompanyOut(CompanyBrief):
    id: int
    website: str | None = None
    careers_url: str | None = None
    linkedin_url: str | None = None
    description: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    employee_count: str | None = None
    founded_year: int | None = None
    open_roles: int = 0


# --- jobs ------------------------------------------------------------------


class MatchOut(CamelModel):
    profile_slug: str
    label: str
    accent: str
    score: float
    matched_terms: list[str] = Field(default_factory=list)


class JobSummary(CamelModel):
    id: int
    title: str
    company: CompanyBrief
    location: str | None = None
    is_remote: bool = False
    is_internship: bool = False
    employment_type: str | None = None
    seniority: str | None = None
    salary_display: str | None = None
    tags: list[str] = Field(default_factory=list)
    posted_at: datetime | None = None
    source: str
    apply_url: str
    top_score: float = 0.0
    matches: list[MatchOut] = Field(default_factory=list)
    excerpt: str = ""


class JobDetail(JobSummary):
    description_text: str = ""
    company_detail: CompanyOut | None = None
    related: list[JobSummary] = Field(default_factory=list)


class FeedResponse(CamelModel):
    items: list[JobSummary]
    next_cursor: str | None = None
    total: int = 0
    generated_at: datetime


class CompanyStackOut(CamelModel):
    """A company plus its open roles — the collapsed stack on the feed screen."""

    company: CompanyBrief
    jobs: list[JobSummary]
    top_score: float = 0.0
    latest_posted_at: datetime | None = None

    @property
    def count(self) -> int:
        return len(self.jobs)


class StackedFeedResponse(CamelModel):
    stacks: list[CompanyStackOut]
    generated_at: datetime


# --- devices ---------------------------------------------------------------


class DeviceRegisterIn(CamelModel):
    apns_token: str = Field(min_length=32, max_length=200)
    install_id: str | None = None
    display_name: str | None = Field(default=None, max_length=80)
    interests: list[str] = Field(default_factory=list)
    push_enabled: bool = True
    internships_only: bool = False
    min_score: float = Field(default=0.55, ge=0.0, le=1.0)
    timezone: str = "Asia/Kolkata"
    quiet_hours_enabled: bool = True
    app_version: str | None = None
    environment: Literal["sandbox", "production"] = "sandbox"


class DevicePatchIn(CamelModel):
    display_name: str | None = Field(default=None, max_length=80)
    interests: list[str] | None = None
    push_enabled: bool | None = None
    internships_only: bool | None = None
    min_score: float | None = Field(default=None, ge=0.0, le=1.0)
    timezone: str | None = None
    quiet_hours_enabled: bool | None = None
    app_version: str | None = None


class DeviceOut(CamelModel):
    id: int
    install_id: str | None = None
    display_name: str | None = None
    interests: list[str]
    push_enabled: bool
    internships_only: bool
    min_score: float
    timezone: str
    quiet_hours_enabled: bool
    created_at: datetime
    last_seen_at: datetime


# --- saved -----------------------------------------------------------------


class SaveIn(CamelModel):
    job_id: int
    state: Literal["saved", "applied", "dismissed"] = "saved"
    note: str | None = None


class SavedJobOut(CamelModel):
    job: JobSummary
    state: str
    note: str | None = None
    created_at: datetime


# --- admin -----------------------------------------------------------------


class IngestOut(CamelModel):
    started_at: datetime
    finished_at: datetime | None = None
    found: int
    created: int
    matched: int
    notifications_sent: int
    sources: list[dict]


class TestPushIn(CamelModel):
    apns_token: str
    job_id: int | None = None


class HealthOut(CamelModel):
    status: str = "ok"
    jobs: int
    devices: int
    apns_configured: bool
    last_ingest_at: datetime | None = None
