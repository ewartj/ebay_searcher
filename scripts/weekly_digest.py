#!/usr/bin/env python3
"""
Weekly trend digest — combines genre price trends and Reddit signals into a
Claude-generated summary sent to your Telegram.

Run weekly (e.g. Sunday evening, after genre_tracker.py has run):
    uv run python scripts/weekly_digest.py
    uv run python scripts/weekly_digest.py --dry-run   # print only, no Telegram

Suggested cron (Sunday 20:00, after genre_tracker at 08:00):
    0 20 * * 0 cd /path/to/ebay_searcher && uv run python scripts/weekly_digest.py
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

import config
from db import _DB_PATH, get_genre_trends, init_db
from notifier import send_telegram_message
from sources.reddit import fetch_signals

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger("weekly_digest")

_MODEL = "claude-haiku-4-5-20251001"


def _build_prompt(trends: list[dict], signals: list[dict]) -> str:
    lines = [
        "You are a secondhand fantasy and sci-fi book market analyst.",
        "Write a concise weekly digest (under 20 lines, plain text, no markdown)",
        "for a UK reseller who focuses on Black Library / Warhammer but also",
        "trades broader fantasy and sci-fi hardbacks.",
        "",
        "Include:",
        "1. Top price movers and what action to take (rising = buy more stock,",
        "   falling = sell before it drops further, stable = hold)",
        "2. Reddit signals worth acting on",
        "3. One specific actionable recommendation for this week",
        "",
    ]

    if trends:
        lines.append("PRICE MOVEMENTS (week-on-week):")
        for t in trends[:12]:
            arrow = "▲" if t["change_pct"] > 0 else "▼"
            lines.append(
                f"  {arrow} {t['label']}: "
                f"£{t['previous_price']:.0f} → £{t['current_price']:.0f} "
                f"({t['change_pct']:+.0%}, {t['listing_count']} listings)"
            )
    else:
        lines.append(
            "PRICE MOVEMENTS: No week-on-week data yet. "
            "Run genre_tracker.py for 2+ weeks to see trends."
        )

    lines.append("")

    if signals:
        lines.append(f"NEWS SIGNALS ({len(signals)} this week):")
        for s in signals[:8]:
            types = ", ".join(s["signal_types"])
            age = f"{s['age_hours']:.0f}h ago"
            lines.append(
                f"  [{types}] {s['source']} ({age}): "
                f"{s['title'][:75]}"
            )
    else:
        lines.append("NEWS SIGNALS: None detected this week.")

    return "\n".join(lines)


def _generate_digest(trends: list[dict], signals: list[dict]) -> str:
    prompt = _build_prompt(trends, signals)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=_MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    if not msg.content:
        log.warning("Claude returned empty content (filtered?); using raw signal list")
        return "(No AI summary available this week — check signals below)"
    digest = msg.content[0].text.strip()

    # Append the 5 most recent signal links so they're clickable in Telegram
    if signals:
        digest += "\n\nNotable links:"
        for s in signals[:5]:
            digest += f"\n  {s['title'][:55]}\n  {s['url']}"

    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and send weekly market digest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print digest to console instead of sending to Telegram",
    )
    args = parser.parse_args()

    init_db()

    if not _DB_PATH.exists():
        log.error("No price history database found. Run main.py and genre_tracker.py first.")
        sys.exit(1)

    log.info("Fetching genre price trends...")
    trends = get_genre_trends(days=28)
    log.info(f"  {len(trends)} label(s) with week-on-week data")

    log.info("Fetching news signals...")
    signals = fetch_signals(config.REDDIT_SUBREDDITS, config.NEWS_FEEDS, days=7)
    log.info(f"  {len(signals)} signal(s) found")

    if not trends and not signals:
        log.info(
            "Nothing to report yet. Run genre_tracker.py for 2+ weeks "
            "to build trend data."
        )
        return

    log.info("Generating digest with Claude...")
    digest = _generate_digest(trends, signals)

    message = f"Warhammer Scout — Weekly Market Digest\n\n{digest}"

    if args.dry_run:
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60)
        log.info("Dry run — digest printed, not sent to Telegram")
    else:
        send_telegram_message(message)
        log.info("Weekly digest sent to Telegram")


if __name__ == "__main__":
    main()
