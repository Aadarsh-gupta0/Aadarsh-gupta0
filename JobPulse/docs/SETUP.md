# Setup

Three stages, each usable on its own: run the backend, run the app against it,
then turn on real push notifications.

---

## 1. Backend

Requires Python 3.11+.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env          # optional; every key has a sane default
```

### Load sample data

```bash
.venv/bin/python -m app.cli seed
```

14 illustrative postings across Google, Figma, Razorpay, Swiggy, Canva, Postman,
Atlassian, Zomato, Linear, Notion, Groww and ISRO. Google gets three roles, so
you can see the notification stack immediately.

### Run

```bash
.venv/bin/python -m app.cli serve --reload
```

- API docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/healthz>

The scheduler starts with the server and re-scrapes every 30 minutes
(`JOBPULSE_INGEST_INTERVAL_MINUTES`). Set `JOBPULSE_DISABLE_SCHEDULER=1` to turn
that off while developing.

### Pull real listings

```bash
.venv/bin/python -m app.cli ingest --no-notify     # scrape, score, store
.venv/bin/python -m app.cli ingest                 # ...and push matches
```

Restrict to specific sources while testing:

```bash
.venv/bin/python -m app.cli ingest --sources remoteok weworkremotely --no-notify
```

### Other commands

```bash
.venv/bin/python -m app.cli profiles               # list interest profiles
.venv/bin/python -m app.cli match "UX Designer" --description "Figma, user research"
.venv/bin/python -m pytest -q                      # 187 tests
```

---

## 2. iOS app

Requires **Xcode 16 or later** (the project uses synchronized file groups) and
targets **iOS 17+**.

```bash
open ios/JobPulse/JobPulse.xcodeproj
```

1. Select the **JobPulse** scheme and any iPhone simulator.
2. In **Signing & Capabilities**, pick your team. Xcode will offer to fix the
   bundle identifier if `com.aadarsh.jobpulse` is taken — accept, and change the
   extension's ID to match (`<your.id>.NotificationService`).
3. Run.

You should land on onboarding: name → interests → notification permission. The
feed populates from the seeded backend.

### Pointing the app at your server

`ios/JobPulse/JobPulse/Info.plist` → `JOBPULSE_API_BASE_URL`.

- Simulator: `http://127.0.0.1:8000` (the default)
- Physical device: `http://<your-mac-lan-ip>:8000`, and start the server with
  `--host 0.0.0.0`

`NSAllowsLocalNetworking` is set so plain HTTP works on your LAN. **Remove that
key from `Info.plist` once you serve the API over HTTPS.**

### If the project ever breaks

The `.xcodeproj` is committed and should just open. If you need to regenerate it:

```bash
brew install xcodegen
cd ios/JobPulse && xcodegen generate
```

---

## 3. Push notifications

Everything above works without this. Real alerts need a paid Apple Developer
account.

### Create an APNs key

1. <https://developer.apple.com/account/resources/authkeys/list> → **+**
2. Enable **Apple Push Notifications service (APNs)**, download the `.p8`.
   **Apple lets you download it once.**
3. Note the **Key ID** (on the key) and your **Team ID** (top right of the portal).

### Configure the server

```bash
mkdir -p backend/secrets
mv ~/Downloads/AuthKey_XXXXXXXXXX.p8 backend/secrets/
```

In `backend/.env`:

```dotenv
JOBPULSE_APNS_TEAM_ID=YOUR_TEAM_ID
JOBPULSE_APNS_KEY_ID=YOUR_KEY_ID
JOBPULSE_APNS_AUTH_KEY_PATH=./secrets/AuthKey_YOUR_KEY_ID.p8
JOBPULSE_APNS_TOPIC=com.aadarsh.jobpulse    # must equal the app's bundle ID
JOBPULSE_APNS_USE_SANDBOX=true              # false for TestFlight / App Store
```

`secrets/` and `*.p8` are gitignored. Restart the server — the "APNs is not
configured" warning should be gone, and `/healthz` should report
`"apnsConfigured": true`.

### Enable the capability in Xcode

Target **JobPulse** → **Signing & Capabilities** → **+ Capability** → **Push
Notifications**. `JobPulse.entitlements` already sets
`aps-environment = development`; switch it to `production` for TestFlight and
set `JOBPULSE_APNS_USE_SANDBOX=false` to match.

### Test it

Push tokens require a **real device** — the simulator will not issue one.

1. Run on your iPhone and accept the notification prompt.
2. The device registers itself; confirm with:
   ```bash
   curl -s localhost:8000/healthz | python3 -m json.tool
   ```
   `devices` should be ≥ 1.
3. Send a test alert:
   ```bash
   curl -X POST localhost:8000/v1/admin/test-push \
     -H 'Content-Type: application/json' \
     -d '{"apnsToken":"<the 64-char hex token>"}'
   ```

Get the token from the Xcode console, or the `devices` table:

```bash
cd backend && .venv/bin/python -c "
from app.db import session_scope
from app.models import Device
from sqlalchemy import select
with session_scope() as s:
    for d in s.scalars(select(Device)):
        print(d.id, d.apns_token, d.interests)
"
```

### Seeing the stack

Lock the phone, then trigger several alerts for one company:

```bash
.venv/bin/python -m app.cli ingest
```

Alerts sharing a company collapse into one lock-screen stack — that is the
`thread-id` in the payload doing the work. Pull down on the stack to fan it out.

---

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Feed empty, "Could not reach the server" | Server not running, or `JOBPULSE_API_BASE_URL` points at `127.0.0.1` from a physical device. |
| Feed empty, no error | No jobs matched. Run `app.cli seed`, or lower **Alert sensitivity** in the You tab. |
| `apnsConfigured: false` | One of the four `JOBPULSE_APNS_*` values is missing, or the `.p8` path is wrong. |
| APNs returns `BadDeviceToken` | Sandbox/production mismatch: `aps-environment` in the entitlements must match `JOBPULSE_APNS_USE_SANDBOX`. |
| APNs returns `DeviceTokenNotForTopic` | `JOBPULSE_APNS_TOPIC` does not equal the app's bundle identifier. |
| No token in the console | Simulators do not issue push tokens. Use a real device. |
| Alerts stop after a while | A dead token retires its device row automatically. Delete the app, reinstall, re-register. |
| Nothing arrives at night | Quiet hours (22:00–07:00 by default). Toggle it off in the You tab. |
| A source returns nothing | Check `scrape_runs` for its error, and run `pytest tests/test_scrapers.py` to see whether the payload shape changed. |
