"""Command line entry points: `python -m app.cli <command>`."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from .db import init_db, session_scope
from .interests import ALL_PROFILES
from .matching import MatchDocument, score_all
from .pipeline import ALL_PROFILE_SLUGS, normalize_raw, persist_draft, run_ingest
from .scrapers import build_scrapers
from .seed import SEED_JOBS

log = logging.getLogger("jobpulse.cli")


def _cmd_ingest(args: argparse.Namespace) -> int:
    init_db()
    scrapers = build_scrapers(args.sources) if args.sources else None
    report = asyncio.run(run_ingest(scrapers, notify=not args.no_notify))
    print(json.dumps(report.as_dict(), indent=2))
    return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    """Load a realistic sample set so the app has content before the first scrape."""
    init_db()
    created = 0
    with session_scope() as session:
        for raw in SEED_JOBS:
            draft = normalize_raw(raw)
            if draft is None:
                continue
            matches = score_all(draft.document, ALL_PROFILE_SLUGS, threshold=0.0)
            _job, was_created = persist_draft(session, draft, matches)
            created += int(was_created)
    print(f"Seeded {created} new jobs ({len(SEED_JOBS)} in the sample set).")
    return 0


def _cmd_match(args: argparse.Namespace) -> int:
    doc = MatchDocument(
        title=args.title,
        company=args.company or "",
        description=args.description or "",
        tags=tuple(args.tags or []),
    )
    results = score_all(doc, ALL_PROFILE_SLUGS, threshold=0.0)
    if not results:
        print("No profile matched.")
        return 0
    for result in results:
        print(f"{result.score:>6.3f}  {result.profile_slug:<16} {', '.join(result.matched_terms)}")
    return 0


def _cmd_profiles(_args: argparse.Namespace) -> int:
    for profile in ALL_PROFILES:
        print(f"{profile.slug:<16} {profile.label:<18} {profile.tagline}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jobpulse", description="JobPulse backend tools")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Run one scrape pass now")
    ingest.add_argument("--sources", nargs="*", help="Limit to these scraper names")
    ingest.add_argument("--no-notify", action="store_true", help="Store matches without pushing")
    ingest.set_defaults(func=_cmd_ingest)

    seed = sub.add_parser("seed", help="Load the bundled sample jobs")
    seed.set_defaults(func=_cmd_seed)

    match = sub.add_parser("match", help="Score one posting against every interest profile")
    match.add_argument("title")
    match.add_argument("--company")
    match.add_argument("--description")
    match.add_argument("--tags", nargs="*")
    match.set_defaults(func=_cmd_match)

    profiles = sub.add_parser("profiles", help="List the interest profiles")
    profiles.set_defaults(func=_cmd_profiles)

    serve = sub.add_parser("serve", help="Run the API with uvicorn")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
