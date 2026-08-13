# Lead Engine

Finds local businesses with weak websites, generates a modern concept
redesign, hosts it for free on GitHub Pages, and reaches out once by email
(or contact form as fallback). Runs on a free stack: GitHub Actions (compute
+ scheduling) + GitHub Pages (hosting) + SQLite (storage, committed to repo)
+ Google Places API (free monthly credit) + Gmail API (free within quota).

## One-time setup

1. **Create a new GitHub repo** and push this code to it.

2. **Enable GitHub Pages**: repo Settings -> Pages -> Source: "Deploy from a
   branch" -> Branch: `gh-pages`. The first real deploy happens automatically
   the first time the daily workflow runs and creates that branch.

3. **Get a Google Places API key** (free):
   - console.cloud.google.com -> new project -> enable "Places API"
   - Create an API key, restrict it to the Places API.
   - Google gives ~$200/month free credit — this pipeline uses roughly
     $5-10/month worth of calls at 5 leads/day, so you'll stay free.

4. **Get a Gmail OAuth token** (free, one-time, run locally — see
   `scripts/generate_gmail_token.py` for full steps). This produces a JSON
   string you'll store as a secret.

5. **Set repo variables** (Settings -> Secrets and variables -> Actions ->
   Variables tab — these are non-secret config):
   - `LEAD_TARGET_LOCATION` — e.g. `Bhubaneswar, Odisha, India`
   - `LEAD_NICHES` — comma-separated, e.g. `dentist,gym,salon,spa`
   - `LEAD_SENDER_NAME` — your name / business name
   - `LEAD_SENDER_EMAIL` — the Gmail address you authorized above
   - `LEAD_SENDER_ADDRESS` — your physical mailing address (CAN-SPAM requires this)
   - `PAGES_BASE_URL` — e.g. `https://yourusername.github.io/lead-engine`

6. **Set repo secrets** (same page, Secrets tab):
   - `GOOGLE_PLACES_API_KEY`
   - `GMAIL_TOKEN_JSON` — the output from step 4

7. Commit an empty `data/` folder (or just let the first run create it).

## Running it

- It runs automatically per the cron schedules in
  `.github/workflows/daily.yml` (weekdays ~4am, adjust the cron for your
  timezone — GitHub cron is UTC) and `weekly_digest.yml` (Fridays 5pm).
- You can also trigger either manually: repo -> Actions tab -> select
  workflow -> "Run workflow".

## Important limits already built in

- Max 5 outreach emails/day (`LEAD_DAILY_CAPACITY`, override with a repo variable)
- Max 30 site visits per run
- One browser session at a time
- Never contacts the same business twice (checked by name+location before any work starts)
- No follow-ups — one outreach per prospect, ever
- Opt-outs (`db.record_opt_out`) are checked before every send
- All copy is built from real scraped data — nothing is fabricated. If
  essential contact info can't be found, the business is skipped rather than
  guessed at.

## Things worth doing before running this for real

- **Read Google's Places API ToS and your target sites' robots.txt** — this
  build uses the official Places API specifically to stay compliant, but
  scraping individual business websites still has some legal nuance
  (generally fine for public contact info, but check).
- **Test on a small batch first** (set `LEAD_DAILY_CAPACITY=1`) before
  scaling to 5/day, to sanity-check the generated site quality and the
  outreach copy.
- **Contact-form fallback will fail often** — many sites use reCAPTCHA or
  custom form structures the generic selectors won't match. Those get logged
  as `failed` for manual review rather than silently dropped.
- **CAN-SPAM applies to the US; if you ever target businesses outside your
  home country**, check local equivalent laws (e.g. Canada's CASL, India's
  IT Act rules on unsolicited commercial email) since the required
  disclosures differ.
