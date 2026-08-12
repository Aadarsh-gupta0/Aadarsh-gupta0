"""RemoteOK — public JSON feed at https://remoteok.com/api."""

from __future__ import annotations

from .base import PoliteClient, RawJob, Scraper

API_URL = "https://remoteok.com/api"


class RemoteOKScraper(Scraper):
    name = "remoteok"
    display_name = "RemoteOK"

    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        payload = await client.get_json(API_URL)
        return self.parse(payload)

    def parse(self, payload: object) -> list[RawJob]:
        if not isinstance(payload, list):
            return []
        jobs: list[RawJob] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            # The feed's first element is a licence notice, not a posting.
            if "legal" in entry and "position" not in entry:
                continue
            job = self._to_raw(entry)
            if job and job.is_usable():
                jobs.append(job)
        return jobs

    def _to_raw(self, entry: dict) -> RawJob | None:
        title = (entry.get("position") or entry.get("title") or "").strip()
        company = (entry.get("company") or "").strip()
        url = entry.get("apply_url") or entry.get("url") or ""
        if not (title and company and url):
            return None

        salary_raw = None
        low, high = entry.get("salary_min"), entry.get("salary_max")
        if low and high:
            salary_raw = f"${int(low):,} - ${int(high):,}"

        tags = [str(t) for t in entry.get("tags") or [] if t]

        return RawJob(
            source=self.name,
            source_id=str(entry.get("id") or entry.get("slug") or url),
            title=title,
            company_name=company,
            apply_url=url,
            description_html=entry.get("description"),
            location=entry.get("location") or "Remote",
            remote_hint=True,  # every RemoteOK posting is remote by definition
            tags=tags,
            salary_raw=salary_raw,
            posted_at=entry.get("date") or entry.get("epoch"),
            company_logo_url=entry.get("company_logo") or entry.get("logo"),
        )
