# Architecture

Notes on the decisions that are not obvious from reading the code.

## The pipeline

```
scrape → normalise → dedupe → score → store → notify
```

One pass runs all sources concurrently (`asyncio.gather`), but the shared
`PoliteClient` paces requests per host, so concurrency across sources never
becomes hammering of any single one. A source that throws is caught, recorded in
`scrape_runs`, and the pass continues — one broken board must not cost you the
other six.

## Dedupe happens before scoring, on content

The same opening is routinely listed on three boards. Deduping on URL would fail
(each board has its own), so the key is a content hash:

```python
fingerprint = sha256(slug(company) | normalised(title) | slug(location))
```

Titles get their board-specific decoration stripped first — `"- Remote"`,
`"(Full-time)"`, `"m/f/d"` — because those suffixes are how the same job ends up
looking like three.

The payoff is at notification time: dedupe is what stops one role from buzzing
your phone three times.

When a duplicate arrives, the richer record wins field by field: a longer
description replaces a thinner one, a salary fills a blank, but nothing already
known is overwritten with less.

## Scoring is transparent, not statistical

An alert you cannot explain is an alert the user turns off. Every profile is a
bag of weighted regex terms, and the terms a job hit are stored on the match row
and surfaced in the app's "Why you're seeing this" block.

```python
score = Σ(term.weight × best_field_weight) × penalty / saturation
```

Four mechanisms do the real work:

**Field weighting.** `title: 3.0, tags: 1.6, description: 1.0, company: 0.4`. A
term counts once, at the best field it appears in. "Flutter Developer" in the
title saturates; "we also use Flutter" in paragraph nine does not.

**Anchor gates.** A profile only scores if the posting is in the right universe
at all. Without this, every backend role mentioning Firebase scores as Flutter.

**Hard negatives.** In the title they disqualify outright — "Product Manager"
can never be a Product Design match. Elsewhere they only dampen (×0.45), because
a real Product Designer posting legitimately mentions working with a PM.

**Description window.** Only the first 2500 characters are scored. Company
boilerplate drifts to the bottom of long posts.

Two thresholds separate *worth showing* from *worth interrupting for*:
`match_threshold` (0.35) gates the feed, `notify_threshold` (0.55, adjustable
per device) gates the push.

## Notification grouping is the product

The `thread-id` in the APNs payload is set to `company-<slug>`. iOS collapses
notifications sharing one into a single stack, so five Google roles arrive as
one expandable group rather than five buzzes.

Three things reinforce it:

- `apns-collapse-id` is per job, so re-sending a job **replaces** its alert
  rather than adding another.
- `relevance-score` carries the match score, so iOS leads a summarised stack
  with the strongest match.
- `mutable-content` lets the notification service extension swap in the company
  logo before the banner draws.

The app's Incoming screen groups by the same key, so the lock screen and the
feed are the same object at two levels of zoom.

Three further guards keep the volume sane: a per-run cap
(`max_pushes_per_device_per_run`), quiet hours evaluated in the *device's*
timezone, and the `deliveries` table — a unique `(device_id, job_id)` means a
job is never pushed to the same device twice, even across restarts.

## Why `@Observable` has no `didSet` here

The Observation macro rewrites tracked stored properties into computed ones, so
a `didSet` observer either fails to compile or silently stops publishing changes
to SwiftUI. Both stores therefore avoid it:

- `PreferencesStore` holds one `UserSettings` value. `RootView` watches it with a
  single `onChange` and calls `settingsChanged()`, which persists to
  `UserDefaults` immediately and debounces a `PATCH` to the server 600ms later.
- `JobStore` exposes plain `filter` / `searchQuery` and the views call
  `filterChanged` / `searchChanged` from `onChange`.

Writes are optimistic throughout: saving a job updates the card instantly and
rolls back only if the server rejects it, which is what keeps swipe gestures
feeling immediate.

## The notification stack

`NotificationStack` is a single `VStack` whose spacing goes **negative** when
collapsed:

```swift
VStack(spacing: isExpanded ? 10 : -(cardHeight - peek)) { … }
```

Each card sits behind the one above with `peek` points showing. Expanding
animates one number, and because view identity never changes, cards slide apart
instead of cross-fading. Depth comes from three cues applied by index — scale,
opacity, and a horizontal inset — which is what makes a collapsed group read as
a pile rather than a list of short rows.

The Home feed gets a similar silhouette for free from `scrollTransition`,
compressing and dimming cards as they approach the viewport edge.

## Glass, specifically

Four layers per panel, in order:

1. a system material, so what is behind is genuinely blurred;
2. a white tint, giving the pane its own body;
3. a top-biased specular highlight, implying a light source;
4. a directional hairline border, brightest where that light lands.

Layer 4 is what separates this from a translucent rectangle — a uniform border
reads as an outline, a directional one reads as glass. It also needs something
to refract, which is why `AuroraBackground` sits behind every screen with three
slow-drifting, heavily blurred colour blobs.

The palette is dark-first and the app pins `.preferredColorScheme(.dark)`.
Glassmorphism depends on saturated light bleeding through a frosted panel, and
that reads as mud on a light ground.

## Scraper design

`parse()` is always a pure function from payload to `[RawJob]`, separate from
`fetch()`, which does the network. That is what makes the fixture tests possible:
each source's real payload shape is recorded in `tests/fixtures/`, so a board
changing its JSON surfaces as a failing test instead of a silently empty feed.

Parsers are deliberately lenient — a malformed row is skipped, not fatal — and
never filter for relevance. Scoring is the pipeline's job; a parser that also
decided what was interesting would be untestable in isolation.

## Data model

`companies` exists separately from `jobs` so the detail screen's company blurb,
stats and links are shared across every role at that employer, and so
`open_roles` is a count rather than a query.

`job_matches` is a row per (job, profile) rather than a single score on the job:
one posting genuinely can be both a UI/UX and a Product Design match, and each
device subscribes to a different subset of profiles.

## Known gaps

- Company metadata (industry, HQ, size, founded) has no source populating it
  yet; the columns and UI exist and degrade to hiding empty rows. A Clearbit-style
  enrichment step or a hand-maintained YAML would fill it.
- Job expiry is not detected. `is_active` exists but nothing flips it when a
  posting disappears from its source; a sweep marking jobs absent for N passes
  would close that.
- The feed paginates by offset. Fine at this scale, but a keyset cursor on
  `(posted_at, id)` would be correct under heavy insert load.
- The iOS app has no test target. The logic worth testing (scoring, dedupe) all
  lives server-side, but `Job.postedRelative` and the salary formatter would
  benefit.
