"""
Price history database.

Records every scan's listings and market prices to SQLite so trends can be
tracked over time. Database is created automatically at data/prices.db.

Schema
------
scans          — one row per scan run (timestamp)
listing_prices — every listing seen in a scan (title, price, source)
market_prices  — market price determined for each priced item in a scan
"""
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import config
from models import Bargain, Listing

log = logging.getLogger(__name__)


def _connect() -> sqlite3.Connection:
    path = Path(config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and indexes if they don't exist. Safe to call on every run."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scans (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS listing_prices (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id    INTEGER NOT NULL REFERENCES scans(id),
                title      TEXT NOT NULL,
                price_gbp  REAL NOT NULL,
                source     TEXT NOT NULL,
                scanned_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_prices (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id      INTEGER NOT NULL REFERENCES scans(id),
                title        TEXT NOT NULL,
                market_price REAL NOT NULL,
                price_source TEXT NOT NULL,
                scanned_at   TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_lp_title    ON listing_prices(title);
            CREATE INDEX IF NOT EXISTS idx_lp_scanned  ON listing_prices(scanned_at);
            CREATE INDEX IF NOT EXISTS idx_mp_title    ON market_prices(title);
            CREATE INDEX IF NOT EXISTS idx_mp_scanned  ON market_prices(scanned_at);

            CREATE TABLE IF NOT EXISTS genre_prices (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                tracked_at    TEXT NOT NULL,
                search_term   TEXT NOT NULL,
                label         TEXT NOT NULL,
                median_price  REAL NOT NULL,
                listing_count INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_gp_label    ON genre_prices(label);
            CREATE INDEX IF NOT EXISTS idx_gp_tracked  ON genre_prices(tracked_at);

            CREATE TABLE IF NOT EXISTS alerted_listings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                url        TEXT NOT NULL UNIQUE,
                alerted_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_al_url      ON alerted_listings(url);
            CREATE INDEX IF NOT EXISTS idx_al_alerted  ON alerted_listings(alerted_at);

            CREATE TABLE IF NOT EXISTS source_counts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id    INTEGER NOT NULL REFERENCES scans(id),
                source     TEXT NOT NULL,
                count      INTEGER NOT NULL,
                scanned_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sc_source   ON source_counts(source);
            CREATE INDEX IF NOT EXISTS idx_sc_scanned  ON source_counts(scanned_at);
        """)


def record_scan(listings: list[Listing], bargains: list[Bargain]) -> int:
    """
    Persist a completed scan to the database.

    Stores every listing price seen (for distribution tracking) and the
    market price established for each bargain (for trend tracking).
    Returns the new scan ID.
    """
    now = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        cur = conn.execute("INSERT INTO scans (scanned_at) VALUES (?)", (now,))
        scan_id = cur.lastrowid

        conn.executemany(
            "INSERT INTO listing_prices (scan_id, title, price_gbp, source, scanned_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [(scan_id, lst.title, lst.price_gbp, lst.source, now) for lst in listings],
        )

        conn.executemany(
            "INSERT INTO market_prices "
            "(scan_id, title, market_price, price_source, scanned_at) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (scan_id, b.listing.title, b.market_price, b.price_source, now)
                for b in bargains
            ],
        )

    log.debug(
        f"DB: scan {scan_id} recorded — "
        f"{len(listings)} listings, {len(bargains)} market prices"
    )
    return scan_id


def get_market_price_history(title: str, days: int = 90) -> list[dict]:
    """
    Return recorded market prices for a title over the last N days.
    Each row: {scanned_at, market_price, price_source}
    """
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
    return [dict(r) for r in rows]


def get_listing_price_distribution(title: str, days: int = 90) -> list[float]:
    """
    Return all individual listing prices seen for a title over the last N days.
    Useful for understanding the spread of asking prices.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT price_gbp FROM listing_prices
            WHERE lower(title) LIKE lower(?)
              AND scanned_at >= datetime('now', ?)
            ORDER BY scanned_at
            """,
            (f"%{title}%", f"-{days} days"),
        ).fetchall()
    return [r["price_gbp"] for r in rows]


def record_genre_prices(snapshots: list[tuple[str, str, dict]]) -> None:
    """
    Store weekly genre price snapshots.
    snapshots: list of (search_term, label, {median, count, min, max})
    """
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO genre_prices "
            "(tracked_at, search_term, label, median_price, listing_count) "
            "VALUES (?, ?, ?, ?, ?)",
            [(now, term, label, stats["median"], stats["count"])
             for term, label, stats in snapshots],
        )
    log.debug(f"DB: recorded {len(snapshots)} genre price snapshots")


def get_genre_trends(days: int = 28) -> list[dict]:
    """
    Return week-over-week price changes for all tracked genre labels.
    Compares the most recent snapshot to the one closest to 7 days before it.
    Each row: {label, current_price, previous_price, change_pct, current_count}
    """
    with _connect() as conn:
        current = {
            row["label"]: {"price": row["median_price"], "count": row["listing_count"]}
            for row in conn.execute(
                """
                SELECT label, median_price, listing_count
                FROM genre_prices g1
                WHERE tracked_at = (
                    SELECT MAX(tracked_at) FROM genre_prices g2
                    WHERE g2.label = g1.label
                      AND g2.tracked_at >= datetime('now', ?)
                )
                """,
                (f"-{days} days",),
            ).fetchall()
        }

        previous = {
            row["label"]: row["median_price"]
            for row in conn.execute(
                """
                SELECT label, median_price
                FROM genre_prices g1
                WHERE tracked_at = (
                    SELECT MAX(tracked_at) FROM genre_prices g2
                    WHERE g2.label = g1.label
                      AND g2.tracked_at < datetime('now', '-6 days')
                )
                """
            ).fetchall()
        }

    trends = []
    for label, cur in current.items():
        if label in previous and previous[label] > 0:
            prev_price = previous[label]
            change_pct = (cur["price"] - prev_price) / prev_price
            trends.append({
                "label": label,
                "current_price": cur["price"],
                "previous_price": prev_price,
                "change_pct": change_pct,
                "listing_count": cur["count"],
            })

    trends.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    return trends


def get_frequent_bargain_titles(days: int = 90, limit: int = 20) -> list[dict]:
    """
    Return titles that appeared most often as bargains, ordered by frequency.
    Each row: {title, count, avg_discount_vs_market}
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                mp.title,
                COUNT(*) AS count,
                AVG(lp.price_gbp / mp.market_price) AS avg_ratio
            FROM market_prices mp
            JOIN listing_prices lp
                ON lower(lp.title) = lower(mp.title)
               AND lp.scan_id = mp.scan_id
            WHERE mp.scanned_at >= datetime('now', ?)
            GROUP BY lower(mp.title)
            ORDER BY count DESC
            LIMIT ?
            """,
            (f"-{days} days", limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Alert deduplication
# ---------------------------------------------------------------------------

def filter_new_alerts(urls: list[str], dedup_days: int = 30) -> list[str]:
    """Return only URLs not already alerted within the last dedup_days days."""
    if not urls:
        return []
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT url FROM alerted_listings
            WHERE url IN ({','.join('?' * len(urls))})
              AND alerted_at >= datetime('now', ?)
            """,
            (*urls, f"-{dedup_days} days"),
        ).fetchall()
    already_seen = {r["url"] for r in rows}
    return [u for u in urls if u not in already_seen]


def record_alerted_urls(urls: list[str]) -> None:
    """Mark URLs as alerted so they won't trigger duplicate notifications."""
    if not urls:
        return
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO alerted_listings (url, alerted_at) VALUES (?, ?)",
            [(url, now) for url in urls],
        )
    log.debug(f"DB: recorded {len(urls)} alerted URL(s)")


# ---------------------------------------------------------------------------
# Source health tracking
# ---------------------------------------------------------------------------

def record_source_counts(scan_id: int, counts: dict[str, int]) -> None:
    """Record how many listings each source returned for a given scan."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO source_counts (scan_id, source, count, scanned_at) VALUES (?, ?, ?, ?)",
            [(scan_id, source, count, now) for source, count in counts.items()],
        )


def get_recent_source_counts(source: str, limit: int = 3) -> list[int]:
    """Return listing counts for the last N scans from a given source, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT count FROM source_counts
            WHERE source = ?
            ORDER BY scanned_at DESC
            LIMIT ?
            """,
            (source, limit),
        ).fetchall()
    return [r["count"] for r in rows]
