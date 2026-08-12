"""Operational endpoints: trigger an ingest, send a test push, inspect health."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select

from ..models import Job
from ..pipeline import run_ingest
from ..push import APNsClient, build_payload, collapse_id_for
from ..schemas import IngestOut, TestPushIn
from .deps import SessionDep, SettingsDep, require_api_key

router = APIRouter(prefix="/v1/admin", tags=["admin"], dependencies=[Depends(require_api_key)])


@router.post("/ingest", response_model=IngestOut)
async def trigger_ingest(
    notify: bool = True,
    sources: Annotated[list[str] | None, Query()] = None,
) -> IngestOut:
    """Run a full scrape pass now instead of waiting for the scheduler."""
    from ..scrapers import build_scrapers

    report = await run_ingest(build_scrapers(sources) if sources else None, notify=notify)
    return IngestOut(**report.as_dict())


@router.post("/test-push")
async def test_push(session: SessionDep, settings: SettingsDep, body: TestPushIn) -> dict:
    """Send one notification to a token so you can check the lock-screen look."""
    if not settings.apns_configured:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "APNs is not configured — set JOBPULSE_APNS_* first.",
        )

    job = (
        session.get(Job, body.job_id)
        if body.job_id
        else session.scalar(select(Job).order_by(Job.ingested_at.desc()).limit(1))
    )
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No job available to send")

    match = max(job.matches, key=lambda m: m.score, default=None)
    payload = build_payload(
        job,
        profile_slug=match.profile_slug if match else "flutter",
        score=match.score if match else 1.0,
        matched_terms=list(match.matched_terms or []) if match else [],
        badge=1,
    )

    async with APNsClient(settings) as client:
        result = await client.send(body.apns_token, payload, collapse_id=collapse_id_for(job))

    return {
        "ok": result.ok,
        "statusCode": result.status_code,
        "apnsId": result.apns_id,
        "reason": result.reason,
        "jobId": job.id,
        "payload": payload,
    }
