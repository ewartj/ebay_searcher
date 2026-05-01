# Changelog

All notable changes to Warhammer Scout are recorded here, newest first.

---

## Unreleased

- **Etsy source** (`sources/etsy.py`) — Etsy API v3 integration; skips silently if `ETSY_API_KEY` unset
- **Buyback floor** (`sources/buyback.py`) — WeBuyBooks ISBN lookup shown in alerts as `| floor £X.XX`
- **ISBN from eBay aspects** — `localizedAspects` parsed for structured ISBN, used by buyback before title regex fallback
- **Feedback loop** — `/good` / `/bad` Telegram commands; stored in DB, injected into Claude filter prompt
- **Cross-source confirmation** — `[multi-source]` flag when same ISBN appears on 2+ sources
- **Stale detection** — `[seen before]` flag when a previously alerted URL reappears
- **Market scout** (`scripts/market_scout.py`) — weekly scoring of 50 candidate niches by price variance and liquidity
- **Subscription box coverage** — Illumicrate, OwlCrate, FairyLoot search terms and price guide entries
- **New fantasy authors** — V.E. Schwab, Leigh Bardugo, Sarah J. Maas, R.F. Kuang, Samantha Shannon, Naomi Novik, Holly Black
- **Exclusions** — `tour stamp`, `event stamp`, `bookplate` added to exclusion list
- **Security** — bot token masked in all exception logs; SQL placeholder pattern commented for clarity

---

## 2026-04-30 — Etsy + bargain improvements (`d0d5b53`)

- Added Etsy source with API v3 integration
- Added WeBuyBooks buyback floor price lookup
- Added feedback loop DB tables and Telegram polling
- Added cross-source ISBN confirmation and stale listing flags
- Expanded fantasy price guide with 6 new authors and 100+ title entries
- Added `NICHE_SCOUT_TERMS` — 50 candidate niches across small press, RPGs, manga, signed editions
- Added `scripts/market_scout.py` with opportunity scoring

## 2026-04-28 — Code review fixes + market scout (`ead72b1`)

- Fixed code review blockers: TextBlock isinstance guard, market scout isolated from critical Lambda path, JSONDecodeError caught in sold-price lookup
- Added Telegram chat ID masking in error logs
- Added `scripts/market_scout.py` skeleton

## 2026-04-26 — Search term refinements (`f92ed12`)

- Cleaned duplicate search terms from config
- Bumped bundle and job-lot search limits

## 2026-04-24 — AWS Lambda deployment (`d4e5194`)

- Full Lambda deployment via Terraform and Docker container image
- S3-backed SQLite persistence between invocations
- EventBridge schedules for daily scan and weekly digest
- CloudWatch alarms → SNS → alert Lambda → Telegram
- CI-ready pytest test suite

## 2026-04-22 — Fantasy/sci-fi category + weekly digest (`1340290`)

- Added fantasy/sci-fi as a second scan category with dedicated Telegram bot
- Added `price_guide_fantasy.py` with 15 authors and 100+ titles
- Added `scripts/genre_tracker.py` and `scripts/weekly_digest.py`
- Added Reddit + RSS signal detection (adaptation, award, scarcity signals)
- Expanded eBay and Vinted search terms for fantasy authors

## 2026-04-21 — Code review + exclusion list (`cd515d8`, `a40b806`)

- Applied AI code review fixes to main scan loop and Vinted source
- Added `EXCLUDE_TITLE_KEYWORDS` to drop codexes, rulebooks, art books before pricing
- Added fast-path `_EXCLUDE_RE` in pricing pipeline

## 2026-04-21 — Core development (`e32ecc3`)

- Added Vinted source with session-cookie auth
- Added bundle detection and separate bundle alerts
- Added `db.py` for price history, alert deduplication, and source health tracking
- Fixed pre-commit blockers

## 2026-04-16 — Initial release (`ad84f3a`)

- eBay Browse API integration with OAuth2 app token
- 4-tier pricing pipeline: price guide → Claude filter → eBay median → Claude estimate
- Warhammer / Black Library price guide
- Basic Telegram bargain alerts
