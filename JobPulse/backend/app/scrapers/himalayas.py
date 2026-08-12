"""Himalayas — remote jobs JSON API."""

from __future__ import annotations

from .base import PoliteClient, RawJob, Scraper

API_URL = "https://himalayas.app/jobs/api"
PAGE_SIZE = 100
MAX_PAGES = 3


class HimalayasScraper(Scraper):
    name = "himalayas"
    display_name = "Himalayas"

    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        jobs: list[RawJob] = []
        seen: set[str] = set()
        for page in range(1, MAX_PAGES + 1):
            offset = (page - 1) * PAGE_SIZE
            payload = await client.get_json(API_URL, params={"limit": PAGE_SIZE, "offset": offset})
            batch = self.parse(payload)
            fresh = [j for j in batch if j.source_id not in seen]
            if not fresh:
                break
            seen.update(j.source_id for j in fresh)
            jobs.extend(fresh)
        return jobs

    def parse(self, payload: object) -> list[RawJob]:
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
            company = (entry.get("companyName") or "").strip()
            url = entry.get("applicationLink") or entry.get("guid") or ""
            if not (title and company and url):
                continue

            salary_raw = None
            low, high = entry.get("minSalary"), entry.get("maxSalary")
            if low and high:
                salary_raw = f"${int(low):,} - ${int(high):,}"

            locations = [str(x) for x in entry.get("locationRestrictions") or [] if x]
            categories = [str(x) for x in entry.get("categories") or [] if x]
            seniority = [str(x) for x in entry.get("seniority") or [] if x]

            jobs.append(
                RawJob(
                    source=self.name,
                    source_id=str(entry.get("guid") or url),
                    title=title,
                    company_name=company,
                    apply_url=url,
                    description_html=entry.get("description") or entry.get("excerpt"),
                    location=", ".join(locations) or "Remote",
                    remote_hint=True,
                    employment_type_raw=", ".join(seniority) or None,
                    tags=categories + seniority,
                    salary_raw=salary_raw,
                    posted_at=entry.get("pubDate"),
                    company_logo_url=entry.get("companyLogo"),
                )
            )
        return jobs
