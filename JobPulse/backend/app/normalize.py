"""Turning messy scraped strings into the fields the app renders."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import UTC, datetime

from selectolax.parser import HTMLParser

_WS_RE = re.compile(r"[ \t ]+")
_NEWLINES_RE = re.compile(r"\n{3,}")
_SLUG_RE = re.compile(r"[^a-z0-9]+")

_BLOCK_TAGS = {"p", "br", "li", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr"}


def strip_html(html: str | None) -> str:
    """Flatten an HTML description to readable plain text."""
    if not html:
        return ""
    if "<" not in html:
        return clean_text(html)
    tree = HTMLParser(html)
    for tag in tree.css("script, style, noscript"):
        tag.decompose()
    for tag in tree.css(",".join(_BLOCK_TAGS)):
        tag.insert_after("\n")
    text = tree.text(separator=" ")
    return clean_text(text)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WS_RE.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = _NEWLINES_RE.sub("\n\n", text)
    return text.strip()


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return _SLUG_RE.sub("-", text.lower()).strip("-") or "unknown"


def fingerprint(company: str, title: str, location: str | None = None) -> str:
    """Content hash used to dedupe the same opening seen on several boards."""
    normalized_title = _SLUG_RE.sub("-", (title or "").lower()).strip("-")
    # Boards decorate titles differently: "(Remote)", "- India", "| Full time".
    normalized_title = re.sub(
        r"-(remote|hybrid|onsite|on-site|full-time|part-time|contract|m-f-d|f-m-d|d-m-w)$",
        "",
        normalized_title,
    )
    parts = [slugify(company), normalized_title, slugify(location or "")]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


# --- remote / location -----------------------------------------------------

_REMOTE_RE = re.compile(
    r"\b(remote|work from home|wfh|distributed|anywhere|telecommut\w*)\b", re.IGNORECASE
)
_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)

_COUNTRY_HINTS = {
    "india": "IN",
    "bengaluru": "IN",
    "bangalore": "IN",
    "hyderabad": "IN",
    "mumbai": "IN",
    "delhi": "IN",
    "gurgaon": "IN",
    "gurugram": "IN",
    "noida": "IN",
    "pune": "IN",
    "chennai": "IN",
    "kolkata": "IN",
    "united states": "US",
    "usa": "US",
    "new york": "US",
    "san francisco": "US",
    "united kingdom": "GB",
    "london": "GB",
    "germany": "DE",
    "berlin": "DE",
    "canada": "CA",
    "singapore": "SG",
    "australia": "AU",
    "netherlands": "NL",
    "amsterdam": "NL",
}


def detect_remote(location: str | None, *extra: str | None) -> bool:
    haystack = " ".join(filter(None, [location, *extra]))[:2000]
    if not haystack:
        return False
    if _HYBRID_RE.search(haystack) and not _REMOTE_RE.search(location or ""):
        return False
    return bool(_REMOTE_RE.search(haystack))


def detect_country(location: str | None) -> str | None:
    if not location:
        return None
    lowered = location.lower()
    for hint, code in _COUNTRY_HINTS.items():
        if hint in lowered:
            return code
    return None


# --- role shape ------------------------------------------------------------

_INTERNSHIP_RE = re.compile(
    r"\b(intern|internship|trainee|apprentice(ship)?|co-?op|summer analyst|graduate program)\b",
    re.IGNORECASE,
)
_NOT_INTERNSHIP_RE = re.compile(r"\binternal\b|\binternational\b", re.IGNORECASE)

_SENIORITY_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("intern", re.compile(r"\b(intern|internship|trainee|apprentice)\b", re.IGNORECASE)),
    (
        "lead",
        re.compile(r"\b(lead|principal|staff|head of|director|vp|chief)\b", re.IGNORECASE),
    ),
    ("senior", re.compile(r"\b(senior|sr\.?|sde\s?(ii|iii|3)|expert)\b", re.IGNORECASE)),
    (
        "junior",
        re.compile(r"\b(junior|jr\.?|entry[- ]level|fresher|graduate|associate)\b", re.IGNORECASE),
    ),
)


def detect_internship(
    title: str, description: str = "", employment_type: str | None = None
) -> bool:
    if employment_type and _INTERNSHIP_RE.search(employment_type):
        return True
    if _INTERNSHIP_RE.search(title) and not _NOT_INTERNSHIP_RE.search(title):
        return True
    # Only trust the description when the signal is close to the top.
    head = description[:400]
    return bool(_INTERNSHIP_RE.search(head) and not _NOT_INTERNSHIP_RE.search(head))


def detect_seniority(title: str, description: str = "") -> str:
    for level, regex in _SENIORITY_RULES:
        if regex.search(title):
            return level
    if _INTERNSHIP_RE.search(description[:300]):
        return "intern"
    if re.search(r"\b([5-9]|1[0-9])\+?\s*years\b", description[:800], re.IGNORECASE):
        return "senior"
    return "mid"


_EMPLOYMENT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("internship", _INTERNSHIP_RE),
    ("contract", re.compile(r"\b(contract|freelance|consultant)\b", re.IGNORECASE)),
    ("part_time", re.compile(r"\bpart[- ]time\b", re.IGNORECASE)),
    ("full_time", re.compile(r"\bfull[- ]time\b", re.IGNORECASE)),
)


def detect_employment_type(title: str, description: str = "", raw: str | None = None) -> str:
    haystack = " ".join(filter(None, [raw, title, description[:400]]))
    for label, regex in _EMPLOYMENT_RULES:
        if regex.search(haystack):
            return label
    return "full_time"


# --- salary ----------------------------------------------------------------

_CURRENCY_SYMBOLS = {"$": "USD", "₹": "INR", "€": "EUR", "£": "GBP", "¥": "JPY"}
_CURRENCY_CODES = ("USD", "INR", "EUR", "GBP", "CAD", "AUD", "SGD")

_SALARY_RE = re.compile(
    r"""
    (?P<sym>[$₹€£¥])?\s*
    (?P<code>USD|INR|EUR|GBP|CAD|AUD|SGD|Rs\.?)?\s*
    (?P<low>\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)
    \s*(?P<lowunit>[kK]|LPA|lpa|lakhs?|L)?\s*
    (?:-|–|—|to)\s*
    (?P<sym2>[$₹€£¥])?\s*
    (?P<high>\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)
    \s*(?P<highunit>[kK]|LPA|lpa|lakhs?|L)?
    """,
    re.VERBOSE,
)

_SINGLE_SALARY_RE = re.compile(
    r"(?P<sym>[$₹€£¥])\s*(?P<amount>\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)\s*(?P<unit>[kK]|LPA|lakhs?)?",
)


def _scale(raw: str, unit: str | None) -> float:
    value = float(raw.replace(",", ""))
    if not unit:
        return value
    unit = unit.lower()
    if unit == "k":
        return value * 1_000
    if unit in {"lpa", "lakh", "lakhs", "l"}:
        return value * 100_000
    return value


def parse_salary(text: str | None) -> tuple[float | None, float | None, str | None, str | None]:
    """Best-effort `(min, max, currency, raw)` out of free-form salary copy."""
    if not text:
        return None, None, None, None
    window = text[:600]

    match = _SALARY_RE.search(window)
    if match:
        currency = _resolve_currency(match.group("sym") or match.group("sym2"), match.group("code"))
        low_unit = match.group("lowunit") or match.group("highunit")
        low = _scale(match.group("low"), low_unit)
        high = _scale(match.group("high"), match.group("highunit") or low_unit)
        if high < low:
            low, high = high, low
        if high > 0:
            return low, high, currency, clean_text(match.group(0))

    single = _SINGLE_SALARY_RE.search(window)
    if single:
        currency = _resolve_currency(single.group("sym"), None)
        amount = _scale(single.group("amount"), single.group("unit"))
        if amount >= 1000:
            return amount, None, currency, clean_text(single.group(0))
    return None, None, None, None


def _resolve_currency(symbol: str | None, code: str | None) -> str | None:
    if symbol and symbol in _CURRENCY_SYMBOLS:
        return _CURRENCY_SYMBOLS[symbol]
    if code:
        upper = code.upper().rstrip(".")
        if upper in _CURRENCY_CODES:
            return upper
        if upper == "RS":
            return "INR"
    return None


# --- time ------------------------------------------------------------------


def to_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_timestamp(value: object) -> datetime | None:
    """Accept epoch seconds, epoch ms, ISO-8601 or RFC-2822 and return aware UTC."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return to_utc(value)
    if isinstance(value, int | float):
        seconds = float(value)
        if seconds > 1e11:  # milliseconds
            seconds /= 1000.0
        try:
            return datetime.fromtimestamp(seconds, tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            return parse_timestamp(int(text))
        try:
            return to_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))
        except ValueError:
            pass
        from email.utils import parsedate_to_datetime

        try:
            return to_utc(parsedate_to_datetime(text))
        except (TypeError, ValueError):
            return None
    return None


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
