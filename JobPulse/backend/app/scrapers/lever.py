"""Lever-hosted boards — official `api.lever.co/v0/postings/{slug}` JSON feed."""

from __future__ import annotations

from ..config import get_settings
from .base import PoliteClient, RawJob, Scraper

BOARD_URL = "https://api.lever.co/v0/postings/{slug}"


class LeverScraper(Scraper):
    name = "lever"
    display_name = "Lever"

    def __init__(self, boards: list[str] | None = None) -> None:
        self.boards = boards if boards is not None else get_settings().lever_boards

    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        jobs: list[RawJob] = []
        for slug in self.boards:
            payload = await client.get_json(BOARD_URL.format(slug=slug), params={"mode": "json"})
            jobs.extend(self.parse(payload, board_slug=slug))
        return jobs

    def parse(self, payload: object, board_slug: str = "") -> list[RawJob]:
        if not isinstance(payload, list):
            return []

        jobs: list[RawJob] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            title = (entry.get("text") or "").strip()
            url = entry.get("hostedUrl") or entry.get("applyUrl") or ""
            if not (title and url):
                continue

            categories = (
                entry.get("categories") if isinstance(entry.get("categories"), dict) else {}
            )
            location = categories.get("location")
            commitment = categories.get("commitment")
            team = categories.get("team")

            tags = [t for t in (team, commitment, entry.get("workplaceType")) if t]

            jobs.append(
                RawJob(
                    source=self.name,
                    source_id=f"{board_slug}:{entry.get('id') or url}",
                    title=title,
                    company_name=board_slug.replace("-", " ").title(),
                    apply_url=url,
                    description_html=entry.get("description") or entry.get("descriptionPlain"),
                    description_text=entry.get("descriptionPlain"),
                    location=location,
                    remote_hint=(entry.get("workplaceType") or "").lower() == "remote" or None,
                    employment_type_raw=commitment,
                    tags=[str(t) for t in tags],
                    posted_at=entry.get("createdAt"),
                    company_website=f"https://jobs.lever.co/{board_slug}",
                )
            )
        return jobs
