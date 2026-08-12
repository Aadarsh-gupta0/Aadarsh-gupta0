"""Test bootstrap.

The environment has to be configured before anything under `app` is imported,
because `app.db` builds its engine at import time.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

_TMP_DIR = Path(tempfile.mkdtemp(prefix="jobpulse-tests-"))

os.environ["JOBPULSE_DATABASE_URL"] = f"sqlite+pysqlite:///{_TMP_DIR / 'test.db'}"
os.environ["JOBPULSE_DISABLE_SCHEDULER"] = "1"
os.environ["JOBPULSE_RESPECT_ROBOTS_TXT"] = "false"
os.environ["JOBPULSE_PER_HOST_DELAY_SECONDS"] = "0"
os.environ.pop("JOBPULSE_API_KEY", None)

import pytest  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(name: str) -> object:
    return json.loads((FIXTURES / name).read_text())


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture(autouse=True)
def fresh_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def session():
    with SessionLocal() as db:
        yield db


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def make_job(
    title: str = "Flutter Developer",
    company: str = "Acme",
    *,
    source_id: str = "1",
    description: str = "Flutter and Dart across iOS and Android.",
    location: str | None = "Bengaluru, India",
    **kwargs,
):
    """Insert one scored job and return its id."""
    from app.db import session_scope
    from app.matching import score_all
    from app.pipeline import ALL_PROFILE_SLUGS, normalize_raw, persist_draft
    from app.scrapers.base import RawJob

    draft = normalize_raw(
        RawJob(
            source="test",
            source_id=source_id,
            title=title,
            company_name=company,
            apply_url=f"https://example.com/{source_id}",
            description_text=description,
            location=location,
            **kwargs,
        )
    )
    assert draft is not None
    with session_scope() as db:
        matches = score_all(draft.document, ALL_PROFILE_SLUGS, threshold=0.0)
        job, _created = persist_draft(db, draft, matches)
        db.flush()
        return job.id
