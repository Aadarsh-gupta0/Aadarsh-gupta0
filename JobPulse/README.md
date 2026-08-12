# JobPulse

Job and internship alerts for **Flutter development, UI/UX and Product Design**,
delivered as iOS push notifications and browsed in a glassmorphic SwiftUI app.

Roles are scraped from public job boards, scored against your interests, and
pushed to your phone **grouped by company** — so five openings at one employer
arrive as one collapsible lock-screen stack rather than five separate buzzes.
The app's feed uses that same grouping, so what lands on your lock screen looks
exactly like what you scroll through later.

```
┌──────────────┐   scrape    ┌──────────────┐   score    ┌──────────────┐
│ 7 job boards │ ──────────▶ │  normalise   │ ─────────▶ │   matching   │
│ (JSON / RSS) │             │  + dedupe    │            │  3 profiles  │
└──────────────┘             └──────────────┘            └──────┬───────┘
                                                                │
                              ┌─────────────────────────────────┤
                              ▼                                 ▼
                       ┌─────────────┐                  ┌──────────────┐
                       │  REST feed  │                  │  APNs push   │
                       │  (FastAPI)  │                  │  thread-id = │
                       └──────┬──────┘                  │   company    │
                              │                         └──────┬───────┘
                              ▼                                ▼
                       ┌────────────────────────────────────────────┐
                       │        SwiftUI app (iOS 17+)               │
                       │  Home · Incoming stacks · Detail · Saved   │
                       └────────────────────────────────────────────┘
```

## What's here

| Path | What it is |
| --- | --- |
| `backend/` | Python scrapers, interest matching, APNs sender, FastAPI |
| `ios/JobPulse/` | SwiftUI app + notification service extension |
| `docs/SETUP.md` | Step-by-step: run the server, run the app, enable push |
| `docs/ARCHITECTURE.md` | How matching, dedupe and notification grouping work |

## Quick start

```bash
# 1. Backend — loads 14 sample jobs so the app has content immediately
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m app.cli seed
.venv/bin/python -m app.cli serve --reload      # http://127.0.0.1:8000/docs

# 2. iOS — open, pick a simulator, run
open ../ios/JobPulse/JobPulse.xcodeproj
```

The app talks to `http://127.0.0.1:8000` by default (`JOBPULSE_API_BASE_URL` in
`ios/JobPulse/JobPulse/Info.plist`). On a physical device, change it to your
Mac's LAN address.

Push notifications need an Apple Developer account — see
[`docs/SETUP.md`](docs/SETUP.md). Everything else (feed, stacking, detail,
saved) works fully without one.

To pull real listings instead of the samples:

```bash
.venv/bin/python -m app.cli ingest --no-notify
```

## The matching engine

Every alert is explainable. Each interest profile is a set of weighted terms
plus hard negatives, and a job's score is traceable to the exact terms it hit —
which is what the "Why you're seeing this" block on the detail screen shows.

```bash
$ .venv/bin/python -m app.cli match "Flutter Developer Intern" \
    --description "Dart, Firebase, BLoC. A 6 month internship."
 1.000  flutter          Flutter, Dart, BLoC, Firebase
```

Three things keep the feed clean:

- **Field weighting** — a term in the title counts 3× what it counts in the body,
  so "Flutter Developer" outranks "we also use Flutter somewhere".
- **Anchor gates** — a job must be in the right universe at all. "Firebase" alone
  never makes something a Flutter role.
- **Hard negatives** — "Product Manager" cannot match Product Design no matter how
  many times the description says *design*.

Two thresholds: jobs scoring ≥ 0.35 appear in the feed, ≥ 0.55 (adjustable per
device in the app) buzz your phone.

## Sources

| Source | Access | Notes |
| --- | --- | --- |
| RemoteOK | public JSON API | remote roles |
| Arbeitnow | public JSON API | EU-heavy, paginated |
| Himalayas | public JSON API | remote roles |
| We Work Remotely | RSS | design / programming / product feeds |
| HN "Who is hiring" | Algolia API | parses the `Company \| Role \| Location` convention |
| Greenhouse | official board API | per-company; configure in `.env` |
| Lever | official board API | per-company; configure in `.env` |
| Internshala | HTML scrape | **off by default**, India internships — see note below |

Everything except Internshala uses a documented public API or feed. Requests go
through a shared client with per-host pacing, retries with backoff, and
robots.txt checks. Internshala is a real HTML scrape, is the most fragile module
in the project, and only runs if you explicitly add it to
`JOBPULSE_ENABLED_SCRAPERS` — enable it only if you have checked that doing so
is acceptable for your use.

## Design

Dark-first glassmorphism, following the Figma mock and the paper sketches:

- **Home** — floating bubbles, serif greeting, All/Popular/New chips, and a feed
  of notification-shaped cards that compress as they approach the edge of the
  viewport.
- **Incoming** — company stacks that fan out on tap, rebuilt from the iOS
  lock-screen behaviour. A `VStack` with *negative* spacing when collapsed, so
  expanding animates one number instead of swapping layouts.
- **Detail** — company blurb, stats grid, links, description, related roles, and
  the match explanation.
- **Glass** — four layers per panel: a system material, a white tint, a
  top-biased specular highlight, and a directional hairline border. A uniform
  border reads as an outline; a directional one reads as glass.

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q     # 187 passing
```

Scraper parsing is tested against recorded fixtures of each source's real
payload shape, so a board changing its JSON shows up as a failing test rather
than a silently empty feed.

## Status

The backend is verified end to end: 187 tests pass, `ruff check`/`format` are
clean, and the API was exercised against seeded data. The iOS app is complete
and reviewed but has **not been compiled** — it was written in a Linux container
with no Xcode. Expect to fix the usual first-build signing settings; see
[`docs/SETUP.md`](docs/SETUP.md).
