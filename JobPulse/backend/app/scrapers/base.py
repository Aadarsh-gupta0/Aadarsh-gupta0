"""Scraper contract plus the polite HTTP client every source shares."""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from ..config import Settings, get_settings

log = logging.getLogger(__name__)


@dataclass
class RawJob:
    """A posting as the source described it, before normalisation."""

    source: str
    source_id: str
    title: str
    company_name: str
    apply_url: str
    description_html: str | None = None
    description_text: str | None = None
    location: str | None = None
    remote_hint: bool | None = None
    employment_type_raw: str | None = None
    salary_raw: str | None = None
    tags: list[str] = field(default_factory=list)
    posted_at: datetime | str | int | float | None = None
    company_logo_url: str | None = None
    company_website: str | None = None

    def is_usable(self) -> bool:
        return bool(self.title and self.company_name and self.apply_url)


class PoliteClient:
    """httpx wrapper adding per-host pacing, retries and robots.txt checks."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = httpx.AsyncClient(
            timeout=self.settings.http_timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": self.settings.user_agent,
                "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def __aenter__(self) -> PoliteClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _lock_for(self, host: str) -> asyncio.Lock:
        lock = self._locks.get(host)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[host] = lock
        return lock

    async def _pace(self, host: str) -> None:
        async with self._lock_for(host):
            last = self._last_request.get(host)
            if last is not None:
                wait = self.settings.per_host_delay_seconds - (time.monotonic() - last)
                if wait > 0:
                    await asyncio.sleep(wait)
            self._last_request[host] = time.monotonic()

    async def allowed(self, url: str) -> bool:
        """Honour robots.txt. A missing or unreadable file is treated as allow."""
        if not self.settings.respect_robots_txt:
            return True
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in self._robots:
            parser: RobotFileParser | None = None
            try:
                response = await self._client.get(f"{origin}/robots.txt", timeout=10.0)
                if response.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
            except httpx.HTTPError:
                parser = None
            self._robots[origin] = parser
        parser = self._robots[origin]
        if parser is None:
            return True
        return parser.can_fetch(self.settings.user_agent, url)

    async def get(self, url: str, **kwargs: object) -> httpx.Response | None:
        if not await self.allowed(url):
            log.warning("robots.txt disallows %s — skipping", url)
            return None

        host = urlparse(url).netloc
        delay = 1.0
        for attempt in range(1, self.settings.http_max_retries + 1):
            await self._pace(host)
            try:
                response = await self._client.get(url, **kwargs)  # type: ignore[arg-type]
            except httpx.HTTPError as exc:
                log.warning(
                    "GET %s failed (%s/%s): %s", url, attempt, self.settings.http_max_retries, exc
                )
            else:
                if response.status_code < 400:
                    return response
                if response.status_code in (429, 500, 502, 503, 504):
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        delay = max(delay, float(retry_after))
                    log.warning("GET %s -> %s, retrying", url, response.status_code)
                else:
                    log.warning("GET %s -> %s, giving up", url, response.status_code)
                    return None
            if attempt < self.settings.http_max_retries:
                await asyncio.sleep(delay)
                delay *= 2
        return None

    async def get_json(self, url: str, **kwargs: object) -> object | None:
        response = await self.get(url, **kwargs)
        if response is None:
            return None
        try:
            return response.json()
        except ValueError:
            log.warning("Response from %s was not JSON", url)
            return None

    async def get_text(self, url: str, **kwargs: object) -> str | None:
        response = await self.get(url, **kwargs)
        return response.text if response is not None else None


class Scraper(ABC):
    """One job source."""

    name: str = "base"
    #: Human-readable, shown in the app's "via …" label.
    display_name: str = "Base"

    @abstractmethod
    async def fetch(self, client: PoliteClient) -> list[RawJob]:
        """Return everything the source is currently advertising."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} {self.name}>"
