"""Background ingest loop."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .config import get_settings
from .pipeline import run_ingest

log = logging.getLogger(__name__)

INGEST_JOB_ID = "jobpulse-ingest"


async def _tick() -> None:
    try:
        await run_ingest()
    except Exception:  # keep the scheduler alive through a bad pass
        log.exception("Scheduled ingest failed")


def create_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        _tick,
        trigger=IntervalTrigger(minutes=settings.ingest_interval_minutes),
        id=INGEST_JOB_ID,
        name="Scrape sources and push new matches",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )
    return scheduler
