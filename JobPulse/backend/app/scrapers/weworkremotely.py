"""We Work Remotely — per-category RSS feeds.

Item titles arrive as "Company: Role", which is where the company name comes
from when the dedicated <company> element is absent.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree

from .base import PoliteClient, RawJob, Scraper

FEEDS = {
    "design": "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "programming": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "product": "https://weworkremotely.com/categories/remote-product-jobs.rss",
}

_TITLE_SPLIT = re.compile(r"\s*:\s*")


class WeWorkRemotelyScraper(Scraper):
    name = "weworkremotely"
    display_name = "We Work Remotely"

    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        jobs: list[RawJob] = []
        seen: set[str] = set()
        for category, url in FEEDS.items():
            xml = await client.get_text(url)
            if not xml:
                continue
            for job in self.parse(xml, category=category):
                if job.source_id not in seen:
                    seen.add(job.source_id)
                    jobs.append(job)
        return jobs

    def parse(self, xml: str, category: str = "") -> list[RawJob]:
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError:
            return []

        jobs: list[RawJob] = []
        for item in root.iter("item"):
            raw_title = _text(item, "title")
            link = _text(item, "link")
            if not (raw_title and link):
                continue

            company = _text(item, "company")
            title = raw_title
            if not company and _TITLE_SPLIT.search(raw_title):
                company, title = _TITLE_SPLIT.split(raw_title, maxsplit=1)
            if not company:
                continue

            region = _text(item, "region") or "Remote"
            item_category = _text(item, "category") or category
            job_type = _text(item, "type")

            tags = [t for t in (item_category, job_type, category) if t]

            jobs.append(
                RawJob(
                    source=self.name,
                    source_id=_text(item, "guid") or link,
                    title=title.strip(),
                    company_name=company.strip(),
                    apply_url=link,
                    description_html=_text(item, "description"),
                    location=region,
                    remote_hint=True,
                    employment_type_raw=job_type,
                    tags=sorted(set(tags)),
                    posted_at=_text(item, "pubDate"),
                )
            )
        return jobs


def _text(item: ElementTree.Element, tag: str) -> str:
    node = item.find(tag)
    if node is None or node.text is None:
        return ""
    return node.text.strip()
