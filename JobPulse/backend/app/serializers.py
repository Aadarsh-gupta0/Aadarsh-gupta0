"""ORM → DTO conversion, including the display strings the app shows verbatim."""

from __future__ import annotations

from .interests import PROFILES_BY_SLUG
from .models import Company, Job
from .normalize import truncate
from .schemas import CompanyBrief, CompanyOut, JobDetail, JobSummary, MatchOut

_SYMBOLS = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "CAD": "C$", "AUD": "A$", "SGD": "S$"}

EXCERPT_LENGTH = 180


def format_amount(value: float, currency: str | None) -> str:
    symbol = _SYMBOLS.get(currency or "", "")
    if currency == "INR":
        if value >= 100_000:
            lakhs = value / 100_000
            trimmed = f"{lakhs:.1f}".rstrip("0").rstrip(".")
            return f"{symbol}{trimmed}L"
        return f"{symbol}{value:,.0f}"
    if value >= 10_000:
        thousands = value / 1_000
        trimmed = f"{thousands:.0f}" if thousands.is_integer() else f"{thousands:.1f}"
        return f"{symbol}{trimmed}k"
    return f"{symbol}{value:,.0f}"


def format_salary(job: Job) -> str | None:
    if job.salary_min and job.salary_max:
        low = format_amount(job.salary_min, job.salary_currency)
        high = format_amount(job.salary_max, job.salary_currency)
        return f"{low} – {high}"
    if job.salary_min:
        return f"From {format_amount(job.salary_min, job.salary_currency)}"
    return job.salary_raw


def company_brief(company: Company | None, fallback_name: str) -> CompanyBrief:
    if company is None:
        return CompanyBrief(slug=fallback_name.lower().replace(" ", "-"), name=fallback_name)
    return CompanyBrief(slug=company.slug, name=company.name, logo_url=company.logo_url)


def company_out(company: Company) -> CompanyOut:
    return CompanyOut(
        id=company.id,
        slug=company.slug,
        name=company.name,
        logo_url=company.logo_url,
        website=company.website,
        careers_url=company.careers_url,
        linkedin_url=company.linkedin_url,
        description=company.description,
        industry=company.industry,
        headquarters=company.headquarters,
        employee_count=company.employee_count,
        founded_year=company.founded_year,
        open_roles=company.open_roles or 0,
    )


def match_out(profile_slug: str, score: float, terms: list[str] | None) -> MatchOut:
    profile = PROFILES_BY_SLUG.get(profile_slug)
    return MatchOut(
        profile_slug=profile_slug,
        label=profile.label if profile else profile_slug,
        accent=profile.accent if profile else "#7C8CFF",
        score=round(score, 3),
        matched_terms=list(terms or [])[:8],
    )


def job_summary(job: Job) -> JobSummary:
    matches = sorted(job.matches, key=lambda m: m.score, reverse=True)
    return JobSummary(
        id=job.id,
        title=job.title,
        company=company_brief(job.company, job.company_name),
        location=job.location,
        is_remote=job.is_remote,
        is_internship=job.is_internship,
        employment_type=job.employment_type,
        seniority=job.seniority,
        salary_display=format_salary(job),
        tags=list(job.tags or [])[:8],
        posted_at=job.posted_at,
        source=job.source,
        apply_url=job.apply_url,
        top_score=round(matches[0].score, 3) if matches else 0.0,
        matches=[match_out(m.profile_slug, m.score, m.matched_terms) for m in matches],
        excerpt=truncate((job.description_text or "").replace("\n", " "), EXCERPT_LENGTH),
    )


def job_detail(job: Job, related: list[Job] | None = None) -> JobDetail:
    summary = job_summary(job)
    return JobDetail(
        **summary.model_dump(by_alias=False),
        description_text=job.description_text or "",
        company_detail=company_out(job.company) if job.company else None,
        related=[job_summary(r) for r in (related or [])],
    )
