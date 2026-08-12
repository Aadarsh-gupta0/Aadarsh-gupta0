"""Greenhouse job boards.

Greenhouse publishes an official read-only JSON board per company, which is the
cleanest way to watch a specific employer (Figma, Razorpay, Postman…) without
scraping HTML. Boards are configured with ``JOBPULSE_GREENHOUSE_BOARDS``.
"""

from __future__ import annotations

import html as html_lib

from ..config import get_settings
from .base import PoliteClient, RawJob, Scraper

BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


class GreenhouseScraper(Scraper):
    name = "greenhouse"
    display_name = "Greenhouse"

    def __init__(self, boards: list[str] | None = None) -> None:
        self.boards = boards if boards is not None else get_settings().greenhouse_boards

    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        jobs: list[RawJob] = []
        for slug in self.boards:
            payload = await client.get_json(BOARD_URL.format(slug=slug), params={"content": "true"})
            jobs.extend(self.parse(payload, board_slug=slug))
        return jobs

    def parse(self, payload: object, board_slug: str = "") -> list[RawJob]:
        if not isinstance(payload, dict):
            return []
        entries = payload.get("jobs")
        if not isinstance(entries, list):
            return []

        jobs: list[RawJob] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            title = (entry.get("title") or "").strip()
            url = entry.get("absolute_url") or ""
            if not (title and url):
                continue

            company = (entry.get("company_name") or "").strip() or board_slug.replace(
                "-", " "
            ).title()

            location = None
            if isinstance(entry.get("location"), dict):
                location = entry["location"].get("name")
            if not location and isinstance(entry.get("offices"), list):
                names = [o.get("name") for o in entry["offices"] if isinstance(o, dict)]
                location = ", ".join(n for n in names if n) or None

            departments = []
            if isinstance(entry.get("departments"), list):
                departments = [
                    d.get("name")
                    for d in entry["departments"]
                    if isinstance(d, dict) and d.get("name")
                ]

            # Greenhouse double-escapes the content field.
            content = entry.get("content") or ""
            if content:
                content = html_lib.unescape(content)

            jobs.append(
                RawJob(
                    source=self.name,
                    source_id=f"{board_slug}:{entry.get('id') or url}",
                    title=title,
                    company_name=company,
                    apply_url=url,
                    description_html=content,
                    location=location,
                    tags=departments,
                    posted_at=entry.get("updated_at") or entry.get("first_published"),
                    company_website=f"https://boards.greenhouse.io/{board_slug}",
                )
            )
        return jobs
