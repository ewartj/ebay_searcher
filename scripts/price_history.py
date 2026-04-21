#!/usr/bin/env python3
"""
Price history report — shows market price trends from scan history.

Usage:
    uv run python scripts/price_history.py              # full report, last 90 days
    uv run python scripts/price_history.py --days 30    # shorter window
    uv run python scripts/price_history.py --title "Saturnine"  # single title
"""
import argparse
import sqlite3
import sys
from pathlib import Path

# Allow imports from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from db import _DB_PATH, _connect, get_frequent_bargain_titles


def _title_trend_report(days: int) -> None:
    """Show market price trends for titles with at least two data points."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                title,
                COUNT(*)                            AS observations,
                MIN(market_price)                   AS min_price,
                MAX(market_price)                   AS max_price,
                AVG(market_price)                   AS avg_price,
                MIN(scanned_at)                     AS first_seen,
                MAX(scanned_at)                     AS last_seen,
                -- First and last price to calculate trend
                MIN(CASE WHEN rn_asc  = 1 THEN market_price END) AS first_price,
                MIN(CASE WHEN rn_desc = 1 THEN market_price END) AS last_price
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY lower(title) ORDER BY scanned_at ASC)  AS rn_asc,
                    ROW_NUMBER() OVER (PARTITION BY lower(title) ORDER BY scanned_at DESC) AS rn_desc
                FROM market_prices
                WHERE scanned_at >= datetime('now', ?)
            )
            GROUP BY lower(title)
            HAVING COUNT(*) >= 2
            ORDER BY ABS(last_price - first_price) / first_price DESC
            """,
            (f"-{days} days",),
        ).fetchall()

    if not rows:
        print("No titles with multiple price observations yet.")
        print("Run the scanner a few more times to build up history.")
        return

    trending_up = [(r, (r["last_price"] - r["first_price"]) / r["first_price"])
                   for r in rows if r["last_price"] > r["first_price"] * 1.05]
    trending_down = [(r, (r["last_price"] - r["first_price"]) / r["first_price"])
                     for r in rows if r["last_price"] < r["first_price"] * 0.95]
    stable = [r for r in rows
              if r not in [x for x, _ in trending_up]
              and r not in [x for x, _ in trending_down]]

    if trending_up:
        print(f"\n{'TRENDING UP':} (consider buying)")
        print("─" * 60)
        for row, pct in sorted(trending_up, key=lambda x: x[1], reverse=True):
            print(
                f"  {row['title'][:45]:<45} "
                f"£{row['first_price']:.0f} → £{row['last_price']:.0f}  "
                f"(+{pct:.0%}, {row['observations']} scans)"
            )

    if trending_down:
        print(f"\nTRENDING DOWN (consider selling)")
        print("─" * 60)
        for row, pct in sorted(trending_down, key=lambda x: x[1]):
            print(
                f"  {row['title'][:45]:<45} "
                f"£{row['first_price']:.0f} → £{row['last_price']:.0f}  "
                f"({pct:.0%}, {row['observations']} scans)"
            )

    if stable:
        print(f"\nSTABLE ({len(stable)} titles within ±5%)")


def _single_title_report(title: str, days: int) -> None:
    """Detailed history for one title."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT scanned_at, market_price, price_source
            FROM market_prices
            WHERE lower(title) LIKE lower(?)
              AND scanned_at >= datetime('now', ?)
            ORDER BY scanned_at
            """,
            (f"%{title}%", f"-{days} days"),
        ).fetchall()

        listing_rows = conn.execute(
            """
            SELECT scanned_at, price_gbp, source
            FROM listing_prices
            WHERE lower(title) LIKE lower(?)
              AND scanned_at >= datetime('now', ?)
            ORDER BY scanned_at
            """,
            (f"%{title}%", f"-{days} days"),
        ).fetchall()

    if not rows:
        print(f"No market price data for {title!r} in the last {days} days.")
        return

    print(f"\nMarket price history: {title!r} (last {days} days)")
    print("─" * 60)
    for r in rows:
        print(f"  {r['scanned_at'][:10]}  £{r['market_price']:.2f}  [{r['price_source']}]")

    prices = [r["market_price"] for r in rows]
    print(f"\n  Min: £{min(prices):.2f}  Max: £{max(prices):.2f}  "
          f"Avg: £{sum(prices)/len(prices):.2f}  ({len(prices)} observations)")

    if listing_rows:
        listing_prices = [r["price_gbp"] for r in listing_rows]
        print(f"\nListing prices seen ({len(listing_rows)} total):")
        print(f"  Min: £{min(listing_prices):.2f}  Max: £{max(listing_prices):.2f}  "
              f"Avg: £{sum(listing_prices)/len(listing_prices):.2f}")


def _frequent_bargains_report(days: int) -> None:
    titles = get_frequent_bargain_titles(days=days, limit=15)
    if not titles:
        print("No bargain frequency data yet.")
        return

    print(f"\nMOST FREQUENT BARGAINS (last {days} days)")
    print("─" * 60)
    for i, row in enumerate(titles, 1):
        avg_discount = 1.0 - row["avg_ratio"]
        print(
            f"  {i:2}. {row['title'][:45]:<45} "
            f"{row['count']} times  (~{avg_discount:.0%} off avg)"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Warhammer Scout price history report")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days")
    parser.add_argument("--title", type=str, default=None, help="Show history for one title")
    args = parser.parse_args()

    if not _DB_PATH.exists():
        print("No price history database found yet.")
        print("Run main.py at least once to start recording data.")
        return

    print(f"=== Warhammer Scout Price History (last {args.days} days) ===")

    if args.title:
        _single_title_report(args.title, args.days)
    else:
        _title_trend_report(args.days)
        _frequent_bargains_report(args.days)


if __name__ == "__main__":
    main()
