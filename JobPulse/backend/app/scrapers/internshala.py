"""Internshala — India-focused internship listings (HTML).

Off by default. Unlike every other source in this package Internshala has no
public API, so this is a real HTML scrape: it is the most fragile module here
and the one most likely to be against a site's wishes. Two guards apply —
`PoliteClient` refuses to fetch anything robots.txt disallows, and the source
only runs when you add ``internshala`` to ``JOBPULSE_ENABLED_SCRAPERS``.

Enable it only if you have checked that it is acceptable for your use.
"""

from __future__ import annotations

import re

from selectolax.parser import HTMLParser, Node

from ..normalize import clean_text
from .base import PoliteClient, RawJob, Scraper

BASE = "https://internshala.com"
SEARCH_URL = BASE + "/internships/keywords-{keyword}/"

DEFAULT_KEYWORDS = ("flutter", "ui-ux-design", "product-design")

_ID_RE = re.compile(r"\d+")


class InternshalaScraper(Scraper):
    name = "internshala"
    display_name = "Internshala"

    def __init__(self, keywords: tuple[str, ...] = DEFAULT_KEYWORDS) -> None:
        self.keywords = keywords

    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        jobs: list[RawJob] = []
        seen: set[str] = set()
        for keyword in self.keywords:
            html = await client.get_text(SEARCH_URL.format(keyword=keyword))
            if not html:
                continue
            for job in self.parse(html):
                if job.source_id not in seen:
                    seen.add(job.source_id)
                    jobs.append(job)
        return jobs

    def parse(self, html: str) -> list[RawJob]:
        tree = HTMLParser(html)
        cards = tree.css("div.individual_internship") or tree.css("div[internshipid]")

        jobs: list[RawJob] = []
        for card in cards:
            job = self._parse_card(card)
            if job and job.is_usable():
                jobs.append(job)
        return jobs

    def _parse_card(self, card: Node) -> RawJob | None:
        title_node = _first(
            card, ["h3.job-internship-name a", ".profile a", "h3 a", ".heading_4_5 a"]
        )
        title = clean_text(title_node.text()) if title_node else ""
        if not title:
            heading = _first(card, ["h3.job-internship-name", ".profile", "h3"])
            title = clean_text(heading.text()) if heading else ""
        if not title:
            return None

        company_node = _first(card, ["p.company-name", ".company_name", ".company h4", ".company"])
        company = clean_text(company_node.text()) if company_node else ""
        if not company:
            return None

        href = title_node.attributes.get("href") if title_node else None
        if not href:
            link = card.css_first("a[href*='/internship/detail/']")
            href = link.attributes.get("href") if link else None
        apply_url = _absolute(href) if href else ""
        if not apply_url:
            return None

        internship_id = (
            card.attributes.get("internshipid")
            or card.attributes.get("data-id")
            or _ID_RE.search(apply_url)
        )
        if hasattr(internship_id, "group"):
            internship_id = internship_id.group(0)
        source_id = str(internship_id or apply_url)

        location_node = _first(
            card, ["#location_names", ".locations", ".location_link", ".row-1-item"]
        )
        location = clean_text(location_node.text()) if location_node else "India"

        stipend_node = _first(card, [".stipend", ".stipend_container_table_cell"])
        stipend = clean_text(stipend_node.text()) if stipend_node else None

        duration = None
        for cell in card.css(".item_body, .row-1-item span"):
            text = clean_text(cell.text())
            if re.search(r"\b\d+\s*month", text, re.IGNORECASE):
                duration = text
                break

        details = " ".join(
            filter(None, [title, company, location, stipend, duration, "Internship"])
        )

        return RawJob(
            source=self.name,
            source_id=source_id,
            title=title,
            company_name=company,
            apply_url=apply_url,
            description_text=details,
            location=location,
            remote_hint="work from home" in location.lower(),
            employment_type_raw="Internship",
            salary_raw=stipend,
            tags=["internship", "india"],
        )


def _first(node: Node, selectors: list[str]) -> Node | None:
    for selector in selectors:
        found = node.css_first(selector)
        if found is not None:
            return found
    return None


def _absolute(href: str) -> str:
    if href.startswith("http"):
        return href
    return BASE + ("" if href.startswith("/") else "/") + href
