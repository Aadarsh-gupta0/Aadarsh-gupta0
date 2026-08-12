"""Scraper registry.

Add a source by writing a `Scraper` subclass and registering its factory here;
`JOBPULSE_ENABLED_SCRAPERS` then decides which ones actually run.
"""

from __future__ import annotations

from collections.abc import Callable

from ..config import get_settings
from .arbeitnow import ArbeitnowScraper
from .base import PoliteClient, RawJob, Scraper
from .greenhouse import GreenhouseScraper
from .himalayas import HimalayasScraper
from .hn_hiring import HackerNewsHiringScraper
from .internshala import InternshalaScraper
from .lever import LeverScraper
from .remoteok import RemoteOKScraper
from .weworkremotely import WeWorkRemotelyScraper

REGISTRY: dict[str, Callable[[], Scraper]] = {
    RemoteOKScraper.name: RemoteOKScraper,
    ArbeitnowScraper.name: ArbeitnowScraper,
    HimalayasScraper.name: HimalayasScraper,
    WeWorkRemotelyScraper.name: WeWorkRemotelyScraper,
    HackerNewsHiringScraper.name: HackerNewsHiringScraper,
    GreenhouseScraper.name: GreenhouseScraper,
    LeverScraper.name: LeverScraper,
    InternshalaScraper.name: InternshalaScraper,
}


def build_scrapers(names: list[str] | None = None) -> list[Scraper]:
    """Instantiate the enabled scrapers, skipping unknown names."""
    selected = names if names is not None else get_settings().enabled_scrapers
    return [REGISTRY[name]() for name in selected if name in REGISTRY]


__all__ = [
    "REGISTRY",
    "ArbeitnowScraper",
    "GreenhouseScraper",
    "HackerNewsHiringScraper",
    "HimalayasScraper",
    "InternshalaScraper",
    "LeverScraper",
    "PoliteClient",
    "RawJob",
    "RemoteOKScraper",
    "Scraper",
    "WeWorkRemotelyScraper",
    "build_scrapers",
]
