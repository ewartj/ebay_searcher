# Warhammer Scout

Daily eBay + Vinted + Etsy bargain finder for Black Library and fantasy/sci-fi collectible hardbacks. Sends Telegram alerts when books are listed below market value, with a weekly market intelligence digest.

## What it does

| Job | Schedule | Output |
|---|---|---|
| Daily scan | Every day 07:00 UTC | Bargain alerts → Telegram (Warhammer bot + Fantasy bot) |
| Weekly digest | Every Sunday 08:00 UTC | Market trend summary + Reddit signals → Telegram (digest bot) |
| Market scout | Every Sunday 08:00 UTC | New niche opportunity report → Telegram (digest bot) |

### Bargain detection pipeline

Each listing goes through four pricing stages in order, stopping at the first hit:

1. **Price guide** — instant lookup against curated known values
2. **Claude filter** — Haiku model drops paperbacks, codexes, and non-prose items; enriched over time with your feedback
3. **eBay active median** — trimmed median of current asking prices for the same title
4. **Claude estimate** — fair-value estimate for anything the above couldn't price

### Signal detection (weekly)

Monitors Reddit (r/fantasy, r/BlackLibrary, r/warhammer40k, and others) plus publisher RSS feeds for adaptation announcements, award wins, author news, and scarcity signals that affect resale values.

### Accuracy improvements

- **Feedback loop** — reply `/good` or `/bad [number]` to a bargain alert; outcomes are stored and injected into Claude's filter prompt so it learns your preferences over time
- **Cross-source confirmation** — bargains whose ISBN appears in listings from multiple sources are flagged `[multi-source]`
- **Stale detection** — listings that were alerted before but are still appearing (haven't sold) are flagged `[seen before]`
- **Buyback floor** — where an ISBN is found, the WeBuyBooks guaranteed buyback price is shown as a risk floor

---

## Sources

| Source | Category | Notes |
|---|---|---|
| eBay | Warhammer + Fantasy | Browse API, GBP BIN listings only |
| Vinted | Warhammer + Fantasy | Session-cookie auth, no key needed |
| Etsy | Warhammer + Fantasy | API v3, requires `ETSY_API_KEY` (free) |

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) configured (`aws configure`)
- [Docker](https://docs.docker.com/engine/install/)
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5

---

## Local setup

```bash
git clone <repo>
cd ebay_searcher

uv sync

cp .env.example .env
# Fill in .env with your credentials (see below)
```

### Credentials

| Variable | Where to get it | Required |
|---|---|---|
| `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` | [developer.ebay.com](https://developer.ebay.com) → Production app | Yes |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | Yes |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | [@BotFather](https://t.me/BotFather) → `/newbot` | Yes |
| `TELEGRAM_DIGEST_BOT_TOKEN` / `TELEGRAM_DIGEST_CHAT_ID` | Same — second bot for weekly digest | Yes |
| `TELEGRAM_FANTASY_BOT_TOKEN` / `TELEGRAM_FANTASY_CHAT_ID` | Same — third bot for fantasy alerts | Optional |
| `ETSY_API_KEY` | [etsy.com/developers](https://www.etsy.com/developers) → Create app → keystring | Optional |

**Getting a Telegram chat ID:** add your bot to a chat, send a message, then visit:
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
Look for `"chat":{"id": ...}`. Group and channel IDs are negative numbers — include the `-` sign.

---

## Running locally

```bash
# Dry run — fetches and prices listings, prints results, sends nothing to Telegram
uv run python main.py --dry-run

# Full run — fetches, prices, and sends Telegram alerts
uv run python main.py

# Weekly jobs
uv run python scripts/genre_tracker.py            # record weekly price snapshots
uv run python scripts/weekly_digest.py            # generate and send market digest
uv run python scripts/weekly_digest.py --dry-run  # print digest to console
uv run python scripts/market_scout.py --dry-run   # print niche opportunity report
```

---

## Feedback loop

After receiving a bargain alert, reply to your Telegram bot:

```
/good          marks all items in the last alert as confirmed buys
/good 1 3      marks items 1 and 3 as confirmed buys
/bad 2         marks item 2 as a false positive
```

Feedback is stored in the SQLite DB. On each subsequent scan, confirmed good/bad examples are injected into Claude's filter prompt so it gradually learns what you actually buy.

---

## Tests

```bash
uv run pytest       # all tests
uv run pytest -v    # verbose
```

---

## Deploying to AWS Lambda

### 1. Provision infrastructure

```bash
cd deploy/terraform

cp terraform.tfvars.example terraform.tfvars
# Fill in terraform.tfvars — all credentials, unique S3 bucket name
# Note: Telegram group/channel chat IDs must include the leading minus sign

terraform init
terraform apply
```

Creates: ECR repository, S3 bucket (SQLite persistence), IAM role, three Lambda functions, EventBridge schedules, CloudWatch alarms, SNS topic.

### 2. Build and deploy

```bash
./deploy/deploy.sh
```

Builds the Docker image, pushes it to ECR, and updates all three Lambda functions (`warhammer-scout`, `warhammer-scout-weekly`, `warhammer-scout-alerts`).

### 3. Test manually

```bash
# Trigger daily scan
aws lambda invoke \
  --function-name warhammer-scout \
  --region eu-west-2 \
  --payload '{}' \
  /tmp/response.json && cat /tmp/response.json

# Trigger weekly digest
aws lambda invoke \
  --function-name warhammer-scout-weekly \
  --region eu-west-2 \
  --payload '{}' \
  /tmp/response.json && cat /tmp/response.json

# Stream live logs
aws logs tail /aws/lambda/warhammer-scout --follow --region eu-west-2
```

A healthy response is `{"statusCode": 200, "body": "ok"}`.

### Re-deploying after code changes

```bash
./deploy/deploy.sh
```

Only re-run `terraform apply` when changing infrastructure config (env vars, schedules, memory, alarms).

---

## Monitoring

```bash
aws logs tail /aws/lambda/warhammer-scout         --region eu-west-2 --follow
aws logs tail /aws/lambda/warhammer-scout-weekly  --region eu-west-2 --follow
```

CloudWatch alarms fire a Telegram message if either Lambda errors or the daily scan hasn't run in 48 hours.

---

## Architecture

```
EventBridge (daily 07:00 UTC)
  └── warhammer-scout Lambda
        ├── Downloads prices.db from S3
        ├── Polls Telegram for /good /bad feedback → stores in DB
        ├── Fetches listings: eBay + Vinted + Etsy (Warhammer + Fantasy terms)
        ├── Detects bundles, prices singles via 4-tier pipeline
        ├── Flags multi-source ISBN matches and stale listings
        ├── Looks up WeBuyBooks buyback floor price per ISBN
        ├── Sends bargain alerts to Telegram
        ├── Stores alert positions for next feedback poll
        └── Uploads prices.db to S3

EventBridge (Sunday 08:00 UTC)
  └── warhammer-scout-weekly Lambda
        ├── Downloads prices.db from S3
        ├── Records weekly eBay median prices per author/series
        ├── Fetches Reddit/RSS market signals
        ├── Asks Claude for a market digest
        ├── Runs market scout for new niche opportunities
        ├── Sends reports to Telegram
        └── Uploads prices.db to S3

CloudWatch Alarms → SNS → warhammer-scout-alerts Lambda → Telegram
```

---

## Project structure

```
├── main.py                     # Daily scan entry point (CLI + Lambda)
├── lambda_handler.py           # Daily Lambda handler (S3 sync wrapper)
├── lambda_weekly_handler.py    # Weekly Lambda handler (S3 sync wrapper)
├── lambda_alert_handler.py     # CloudWatch alarm → Telegram forwarder
├── config.py                   # Credentials, thresholds, search terms
├── pricing.py                  # 4-tier pricing pipeline
├── notifier.py                 # Telegram formatting, sending, feedback polling
├── db.py                       # SQLite schema, dedup, price history, feedback store
├── models.py                   # Listing and Bargain dataclasses
├── price_guide.py              # Warhammer / Black Library price guide
├── price_guide_fantasy.py      # Fantasy / sci-fi price guide (incl. subscription boxes)
├── sources/
│   ├── __init__.py             # Source registry
│   ├── ebay.py                 # eBay Browse API (extracts ISBN from aspects)
│   ├── vinted.py               # Vinted listing fetcher
│   ├── etsy.py                 # Etsy API v3 listing fetcher
│   ├── buyback.py              # WeBuyBooks buyback floor price lookup
│   ├── ebay_market.py          # eBay active-listing price lookup
│   └── reddit.py               # Reddit/RSS market signal fetcher
├── scripts/
│   ├── genre_tracker.py        # Weekly price snapshot recorder
│   ├── weekly_digest.py        # Weekly market digest generator
│   ├── market_scout.py         # Weekly niche opportunity scorer
│   ├── price_history.py        # CLI price history report
│   └── refresh_price_guide.py  # Price guide update helper
├── deploy/
│   ├── deploy.sh               # Build, push, update Lambda
│   ├── Dockerfile.lambda       # Lambda container image
│   └── terraform/              # AWS infrastructure as code
└── tests/                      # pytest test suite (259 tests)
```

See [CHANGELOG.md](CHANGELOG.md) for the full version history.
