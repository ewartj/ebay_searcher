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
