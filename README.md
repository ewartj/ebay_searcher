# Warhammer Scout

Daily eBay + Vinted bargain finder for Black Library and fantasy/sci-fi hardbacks. Sends Telegram alerts when collectible books are listed below market value.

## What it does

| Job | Schedule | Output |
|---|---|---|
| Daily scan | Every day 07:00 UTC | Bargain alerts → Telegram (Warhammer bot + Fantasy bot) |
| Weekly digest | Every Sunday 08:00 UTC | Market trend summary → Telegram (digest bot) |

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

### Credentials needed

| Variable | Where to get it |
|---|---|
| `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` | [developer.ebay.com](https://developer.ebay.com) → Production app |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | [@BotFather](https://t.me/BotFather) → `/newbot`; chat ID via `getUpdates` |
| `TELEGRAM_DIGEST_BOT_TOKEN` / `TELEGRAM_DIGEST_CHAT_ID` | Same — second bot for weekly digest |
| `TELEGRAM_FANTASY_BOT_TOKEN` / `TELEGRAM_FANTASY_CHAT_ID` | Same — third bot for fantasy alerts (optional) |

To get a chat ID after creating a bot: add it to your chat, send a message, then visit:
```
https://api.telegram.org/bot<TOKEN>/getUpdates
```
Look for `"chat":{"id": ...}` in the response.

---

## Running locally

```bash
# Dry run — fetches and prices listings, prints results, sends nothing
uv run python main.py --dry-run

# Full run — fetches, prices, and sends Telegram alerts
uv run python main.py

# Weekly digest (run genre tracker first, then digest)
uv run python scripts/genre_tracker.py
uv run python scripts/weekly_digest.py

# Dry run digest (prints to console, no Telegram)
uv run python scripts/weekly_digest.py --dry-run
```

---

## Tests

```bash
uv run pytest          # all tests
uv run pytest -v       # verbose
```

---

## Deploying to AWS Lambda

### 1. Provision infrastructure

```bash
cd deploy/terraform

cp terraform.tfvars.example terraform.tfvars
# Fill in terraform.tfvars with all credentials and a unique S3 bucket name

terraform init
terraform apply
```

This creates: ECR repository, S3 bucket (SQLite persistence), IAM role, three Lambda functions, EventBridge schedules, CloudWatch alarms, SNS topic.

### 2. Build and push the container image

Run this from the project root:

```bash
./deploy/deploy.sh
```

Builds the Docker image, pushes it to ECR, and updates all three Lambda functions.

### 3. Test manually

```bash
# Daily scan
aws lambda invoke \
  --function-name warhammer-scout \
  --region eu-west-2 \
  --log-type Tail \
  --cli-read-timeout 0 \
  --query 'LogResult' --output text \
  response.json | base64 --decode && cat response.json

# Weekly digest
aws lambda invoke \
  --function-name warhammer-scout-weekly \
  --region eu-west-2 \
  --log-type Tail \
  --cli-read-timeout 0 \
  --query 'LogResult' --output text \
  response.json | base64 --decode && cat response.json
```

A healthy response is `{"statusCode": 200, "body": "ok"}`.

### Re-deploying after code changes

```bash
./deploy/deploy.sh
```

Only run `terraform apply` again if you change infrastructure (schedules, memory, environment variables, alarms).

---

## Monitoring

**CloudWatch Logs:**
```bash
aws logs tail /aws/lambda/warhammer-scout --region X --follow
aws logs tail /aws/lambda/warhammer-scout-weekly --region X--follow
```

**CloudWatch Alarms** fire a Telegram message to the Warhammer bot if:
- Either Lambda returns an error
- The daily scan has not run in 48 hours

---

## Architecture

```
EventBridge (daily 07:00 UTC)
  └── warhammer-scout Lambda
        ├── Downloads prices.db from S3
        ├── Fetches eBay + Vinted listings
        ├── Prices via: price guide → Claude filter → eBay median → Claude estimate
        ├── Sends bargain alerts to Telegram
        └── Uploads prices.db to S3

EventBridge (Sunday 08:00 UTC)
  └── warhammer-scout-weekly Lambda
        ├── Downloads prices.db from S3
        ├── Records weekly eBay median prices per author/series
        ├── Fetches Reddit/RSS signals
        ├── Asks Claude to generate a market digest
        ├── Sends digest to Telegram
        └── Uploads prices.db to S3

CloudWatch Alarms → SNS → warhammer-scout-alerts Lambda → Telegram
```

## Project structure

```
├── main.py                     # Daily scan entry point (CLI + Lambda)
├── lambda_handler.py           # Daily Lambda handler (S3 sync wrapper)
├── lambda_weekly_handler.py    # Weekly Lambda handler (S3 sync wrapper)
├── lambda_alert_handler.py     # CloudWatch alarm → Telegram forwarder
├── config.py                   # Credentials, thresholds, search terms
├── pricing.py                  # 4-tier pricing pipeline
├── notifier.py                 # Telegram message formatting and sending
├── db.py                       # SQLite schema, dedup, price history
├── models.py                   # Listing and Bargain dataclasses
├── price_guide.py              # Warhammer / Black Library price guide
├── price_guide_fantasy.py      # Fantasy / sci-fi price guide
├── sources/
│   ├── ebay.py                 # eBay Browse API listing fetcher
│   ├── vinted.py               # Vinted listing fetcher
│   ├── ebay_market.py          # eBay active-listing price lookup
│   └── reddit.py               # Reddit/RSS market signal fetcher
├── scripts/
│   ├── genre_tracker.py        # Weekly price snapshot recorder
│   ├── weekly_digest.py        # Weekly market digest generator
│   ├── price_history.py        # CLI price history report
│   └── refresh_price_guide.py  # Price guide update helper
├── deploy/
│   ├── deploy.sh               # Build, push, update Lambda
│   ├── Dockerfile.lambda       # Lambda container image
│   └── terraform/              # AWS infrastructure as code
└── tests/                      # pytest test suite
```
