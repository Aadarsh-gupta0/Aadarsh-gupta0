"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from .api import admin_router, devices_router, jobs_router
from .api.deps import SessionDep, SettingsDep
from .config import get_settings
from .db import init_db
from .models import Device, Job, ScrapeRun
from .scheduler import create_scheduler
from .schemas import HealthOut

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
log = logging.getLogger("jobpulse")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()

    scheduler = None
    # Disable in tests and when running one-off management commands.
    if os.getenv("JOBPULSE_DISABLE_SCHEDULER", "").lower() not in {"1", "true", "yes"}:
        scheduler = create_scheduler()
        scheduler.start()
        log.info("Ingest scheduler running every %s minutes", settings.ingest_interval_minutes)

    if not settings.apns_configured:
        log.warning("APNs is not configured — notifications will be recorded but not delivered.")

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="JobPulse",
    version="0.1.0",
    summary="Job and internship alerts matched to Flutter, UI/UX and Product Design",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(devices_router)
app.include_router(admin_router)


@app.get("/healthz", response_model=HealthOut, tags=["meta"])
def healthz(session: SessionDep, settings: SettingsDep) -> HealthOut:
    last_run = session.scalar(
        select(ScrapeRun.finished_at)
        .where(ScrapeRun.finished_at.is_not(None))
        .order_by(ScrapeRun.finished_at.desc())
        .limit(1)
    )
    return HealthOut(
        status="ok",
        jobs=session.scalar(select(func.count(Job.id))) or 0,
        devices=session.scalar(select(func.count(Device.id))) or 0,
        apns_configured=settings.apns_configured,
        last_ingest_at=last_run,
    )
