"""Tests for db.py — genre price storage and trend calculation."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

import db
from db import get_genre_trends, init_db, record_genre_prices


@pytest.fixture
def temp_db(tmp_path):
    """Patch _DB_PATH to a temp file and initialise the schema."""
    db_path = tmp_path / "test_prices.db"
    with patch.object(db, "_DB_PATH", db_path):
        init_db()
        yield db_path


def _snapshot(term: str, label: str, median: float, count: int = 10) -> tuple:
    return (term, label, {"median": median, "count": count, "min": median * 0.5, "max": median * 1.5})


class TestRecordGenrePrices:
    def test_stores_snapshots(self, temp_db):
        with patch.object(db, "_DB_PATH", temp_db):
            record_genre_prices([_snapshot("joe abercrombie hardback", "Joe Abercrombie", 25.0)])
            import sqlite3
            conn = sqlite3.connect(temp_db)
            rows = conn.execute("SELECT * FROM genre_prices").fetchall()
            conn.close()
        assert len(rows) == 1

    def test_stores_correct_values(self, temp_db):
        with patch.object(db, "_DB_PATH", temp_db):
            record_genre_prices([_snapshot("joe abercrombie hardback", "Joe Abercrombie", 25.0, count=15)])
            import sqlite3
            conn = sqlite3.connect(temp_db)
            row = conn.execute("SELECT * FROM genre_prices").fetchone()
            conn.close()
        assert row[3] == "Joe Abercrombie"  # label
        assert row[4] == 25.0               # median_price
        assert row[5] == 15                 # listing_count

    def test_stores_multiple_snapshots(self, temp_db):
        with patch.object(db, "_DB_PATH", temp_db):
            snapshots = [
                _snapshot("joe abercrombie hardback", "Joe Abercrombie", 25.0),
                _snapshot("brandon sanderson hardback", "Brandon Sanderson", 35.0),
            ]
            record_genre_prices(snapshots)
            import sqlite3
            conn = sqlite3.connect(temp_db)
            count = conn.execute("SELECT COUNT(*) FROM genre_prices").fetchone()[0]
            conn.close()
        assert count == 2


class TestGetGenreTrends:
    def _insert_snapshot(self, db_path: Path, label: str, median: float, tracked_at: str):
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO genre_prices (tracked_at, search_term, label, median_price, listing_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (tracked_at, label.lower(), label, median, 10),
        )
        conn.commit()
        conn.close()

    def test_returns_empty_with_no_data(self, temp_db):
        with patch.object(db, "_DB_PATH", temp_db):
            trends = get_genre_trends()
        assert trends == []

    def test_returns_empty_with_only_one_snapshot(self, temp_db):
        now = datetime.now(timezone.utc).isoformat()
        self._insert_snapshot(temp_db, "Joe Abercrombie", 25.0, now)
        with patch.object(db, "_DB_PATH", temp_db):
            trends = get_genre_trends()
        assert trends == []

    def test_detects_price_increase(self, temp_db):
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=8)
        self._insert_snapshot(temp_db, "Joe Abercrombie", 20.0, week_ago.isoformat())
        self._insert_snapshot(temp_db, "Joe Abercrombie", 25.0, now.isoformat())
        with patch.object(db, "_DB_PATH", temp_db):
            trends = get_genre_trends()
        assert len(trends) == 1
        assert trends[0]["label"] == "Joe Abercrombie"
        assert trends[0]["current_price"] == 25.0
        assert trends[0]["previous_price"] == 20.0
        assert pytest.approx(trends[0]["change_pct"], abs=0.001) == 0.25

    def test_detects_price_decrease(self, temp_db):
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=8)
        self._insert_snapshot(temp_db, "Brandon Sanderson", 40.0, week_ago.isoformat())
        self._insert_snapshot(temp_db, "Brandon Sanderson", 30.0, now.isoformat())
        with patch.object(db, "_DB_PATH", temp_db):
            trends = get_genre_trends()
        assert len(trends) == 1
        assert trends[0]["change_pct"] == pytest.approx(-0.25, abs=0.001)

    def test_sorted_by_absolute_change_descending(self, temp_db):
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=8)
        # Abercrombie: +25% change
        self._insert_snapshot(temp_db, "Joe Abercrombie", 20.0, week_ago.isoformat())
        self._insert_snapshot(temp_db, "Joe Abercrombie", 25.0, now.isoformat())
        # Sanderson: -50% change (larger absolute)
        self._insert_snapshot(temp_db, "Brandon Sanderson", 40.0, week_ago.isoformat())
        self._insert_snapshot(temp_db, "Brandon Sanderson", 20.0, now.isoformat())
        with patch.object(db, "_DB_PATH", temp_db):
            trends = get_genre_trends()
        assert trends[0]["label"] == "Brandon Sanderson"
        assert trends[1]["label"] == "Joe Abercrombie"

    def test_includes_listing_count(self, temp_db):
        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=8)
        self._insert_snapshot(temp_db, "Joe Abercrombie", 20.0, week_ago.isoformat())
        self._insert_snapshot(temp_db, "Joe Abercrombie", 25.0, now.isoformat())
        with patch.object(db, "_DB_PATH", temp_db):
            trends = get_genre_trends()
        assert "listing_count" in trends[0]
        assert trends[0]["listing_count"] == 10
