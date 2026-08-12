"""Arbeitnow job board — free JSON API, paginated."""

from __future__ import annotations

from .base import PoliteClient, RawJob, Scraper

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 5


class ArbeitnowScraper(Scraper):
    name = "arbeitnow"
    display_name = "Arbeitnow"

    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        jobs: list[RawJob] = []
        seen: set[str] = set()
        for page in range(1, MAX_PAGES + 1):
            payload = await client.get_json(API_URL, params={"page": page})
            batch = self.parse(payload)
            if not batch:
                break
            fresh = [j for j in batch if j.source_id not in seen]
            seen.update(j.source_id for j in fresh)
            jobs.extend(fresh)
            if not fresh:
                break
        return jobs

    def parse(self, payload: object) -> list[RawJob]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if not isinstance(data, list):
            return []

        jobs: list[RawJob] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            title = (entry.get("title") or "").strip()
            company = (entry.get("company_name") or "").strip()
            url = entry.get("url") or ""
            if not (title and company and url):
                continue

            job_types = [str(t) for t in entry.get("job_types") or [] if t]
            tags = [str(t) for t in entry.get("tags") or [] if t]

            jobs.append(
                RawJob(
                    source=self.name,
                    source_id=str(entry.get("slug") or url),
                    title=title,
                    company_name=company,
                    apply_url=url,
                    description_html=entry.get("description"),
                    location=entry.get("location"),
                    remote_hint=bool(entry.get("remote")),
                    employment_type_raw=", ".join(job_types) or None,
                    tags=tags + job_types,
                    posted_at=entry.get("created_at"),
                )
            )
        return jobs
