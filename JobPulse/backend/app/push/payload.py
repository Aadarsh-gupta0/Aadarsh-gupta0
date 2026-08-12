"""Building the APNs payload for a job alert.

Two fields do the heavy lifting for the look the app is after:

* ``thread-id`` — iOS groups notifications that share one into a single
  collapsible stack on the lock screen. Grouping by company is what turns five
  Google postings into one "Google" stack the user can fan out, exactly like
  the reference screenshot.
* ``mutable-content`` — lets the Notification Service Extension swap in the
  company logo as an attachment before the banner is drawn.
"""

from __future__ import annotations

from typing import Any

from ..interests import PROFILES_BY_SLUG
from ..models import Job
from ..normalize import slugify, truncate

MAX_BODY = 160


def thread_id_for(job: Job) -> str:
    """Company-level grouping key."""
    return f"company-{slugify(job.company_name)}"


def collapse_id_for(job: Job) -> str:
    """Replaces an earlier alert for the same posting instead of adding one."""
    return f"job-{job.id}"


def relevance_score(score: float) -> float:
    """APNs uses this to pick which alert leads a summarised stack."""
    return round(min(1.0, max(0.0, score)), 2)


def _subtitle(job: Job) -> str:
    bits: list[str] = []
    if job.is_internship:
        bits.append("Internship")
    if job.is_remote:
        bits.append("Remote")
    elif job.location:
        bits.append(job.location)
    if job.salary_raw:
        bits.append(job.salary_raw)
    return " · ".join(bits[:3])


def _body(job: Job, matched_terms: list[str]) -> str:
    if job.description_text:
        summary = job.description_text.split("\n")[0]
        if len(summary) > 40:
            return truncate(summary, MAX_BODY)
    if matched_terms:
        return "Matches " + ", ".join(matched_terms[:4])
    return truncate(job.title, MAX_BODY)


def build_payload(
    job: Job,
    *,
    profile_slug: str,
    score: float,
    matched_terms: list[str] | None = None,
    badge: int | None = None,
) -> dict[str, Any]:
    matched_terms = matched_terms or []
    profile = PROFILES_BY_SLUG.get(profile_slug)

    aps: dict[str, Any] = {
        "alert": {
            "title": job.company_name,
            "subtitle": truncate(job.title, 80),
            "body": _body(job, matched_terms),
        },
        "sound": "default",
        "thread-id": thread_id_for(job),
        "interruption-level": "active",
        "relevance-score": relevance_score(score),
        "mutable-content": 1,
        "category": "JOB_ALERT",
    }
    if badge is not None:
        aps["badge"] = badge

    return {
        "aps": aps,
        # Custom keys the app reads to deep-link and to render the rich banner.
        "jobId": job.id,
        "profile": profile_slug,
        "profileLabel": profile.label if profile else profile_slug,
        "accent": profile.accent if profile else "#7C8CFF",
        "score": round(score, 3),
        "matchedTerms": matched_terms[:6],
        "companyName": job.company_name,
        "companySlug": slugify(job.company_name),
        "logoUrl": job.company.logo_url if job.company else None,
        "applyUrl": job.apply_url,
        "isInternship": job.is_internship,
        "isRemote": job.is_remote,
        "location": job.location,
        "postedAt": job.posted_at.isoformat() if job.posted_at else None,
        "deepLink": f"jobpulse://job/{job.id}",
    }
