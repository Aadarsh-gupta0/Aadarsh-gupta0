"""Hacker News "Ask HN: Who is hiring?" via the public Algolia search API.

Top-level comments in that thread follow a loose convention:

    Company | Role | Location | REMOTE | Salary | https://apply.example.com

so the first line carries most of the structure and the rest is prose.
"""

from __future__ import annotations

import re

from ..normalize import strip_html
from .base import PoliteClient, RawJob, Scraper

SEARCH_URL = "https://hn.algolia.com/api/v1/search"
COMMENTS_PER_PAGE = 100
MAX_COMMENT_PAGES = 4

_URL_RE = re.compile(r"https?://[^\s<>\"')]+")
_SEPARATOR_RE = re.compile(r"\s*\|\s*|\s+[–—]\s+")
_ROLE_HINT_RE = re.compile(
    r"engineer|developer|designer|intern|manager|scientist|analyst|architect|lead|devops|sre",
    re.IGNORECASE,
)
_NOISE_RE = re.compile(
    r"^(remote|onsite|on-site|hybrid|full[- ]time|part[- ]time|contract|visa|"
    r"anywhere|worldwide|us|usa|uk|eu|europe|india)$",
    re.IGNORECASE,
)


class HackerNewsHiringScraper(Scraper):
    name = "hn_hiring"
    display_name = "HN Who is Hiring"

    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        story_id = await self._latest_thread_id(client)
        if not story_id:
            return []

        jobs: list[RawJob] = []
        for page in range(MAX_COMMENT_PAGES):
            payload = await client.get_json(
                SEARCH_URL,
                params={
                    "tags": f"comment,story_{story_id}",
                    "hitsPerPage": COMMENTS_PER_PAGE,
                    "page": page,
                },
            )
            batch = self.parse(payload)
            jobs.extend(batch)
            if not isinstance(payload, dict) or page >= int(payload.get("nbPages", 0)) - 1:
                break
        return jobs

    async def _latest_thread_id(self, client: PoliteClient) -> str | None:
        payload = await client.get_json(
            SEARCH_URL,
            params={
                "tags": "story,author_whoishiring",
                "query": "who is hiring",
                "hitsPerPage": 5,
            },
        )
        if not isinstance(payload, dict):
            return None
        hits = payload.get("hits") or []
        for hit in hits:
            if isinstance(hit, dict) and "hiring" in (hit.get("title") or "").lower():
                return str(hit.get("objectID"))
        return None

    def parse(self, payload: object) -> list[RawJob]:
        if not isinstance(payload, dict):
            return []
        hits = payload.get("hits")
        if not isinstance(hits, list):
            return []

        jobs: list[RawJob] = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            job = self._parse_comment(hit)
            if job and job.is_usable():
                jobs.append(job)
        return jobs

    def _parse_comment(self, hit: dict) -> RawJob | None:
        body = strip_html(hit.get("comment_text") or "")
        if len(body) < 40:
            return None

        first_line = next((ln.strip() for ln in body.split("\n") if ln.strip()), "")
        if not first_line:
            return None

        parts = [p.strip() for p in _SEPARATOR_RE.split(first_line) if p.strip()]
        if not parts:
            return None

        company = parts[0][:120]
        # A bare URL as the leading token means the convention was not followed.
        if company.startswith("http") or len(company) > 90:
            return None

        title = next(
            (p for p in parts[1:] if _ROLE_HINT_RE.search(p) and not _NOISE_RE.match(p)),
            "",
        )
        if not title:
            return None

        location = next(
            (p for p in parts[1:] if p != title and not _URL_RE.match(p) and len(p) < 60),
            None,
        )

        url_match = _URL_RE.search(body)
        apply_url = (
            url_match.group(0)
            if url_match
            else f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        )

        return RawJob(
            source=self.name,
            source_id=str(hit.get("objectID")),
            title=title[:200],
            company_name=company,
            apply_url=apply_url,
            description_text=body,
            location=location,
            remote_hint=bool(re.search(r"\bremote\b", first_line, re.IGNORECASE)),
            tags=["hackernews"],
            posted_at=hit.get("created_at_i") or hit.get("created_at"),
        )
