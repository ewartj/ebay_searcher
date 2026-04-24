"""Tests for scripts/genre_tracker.py — run_genre_tracker return values."""
from unittest.mock import patch

import pytest

import config
from scripts.genre_tracker import run_genre_tracker


@pytest.fixture(autouse=True)
def _mock_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch.object(config, "DB_PATH", db_path), \
         patch("scripts.genre_tracker.init_db"), \
         patch("scripts.genre_tracker.record_genre_prices") as mock_record:
        yield mock_record


class TestRunGenreTracker:
    def test_returns_1_when_all_fetches_fail(self, _mock_db):
        with patch("scripts.genre_tracker.fetch_market_stats", return_value={}):
            result = run_genre_tracker()
        assert result == 1

    def test_does_not_record_when_all_fetches_fail(self, _mock_db):
        with patch("scripts.genre_tracker.fetch_market_stats", return_value={}):
            run_genre_tracker()
        _mock_db.assert_not_called()

    def test_returns_0_when_snapshots_recorded(self, _mock_db):
        stats = {"joe abercrombie hardback": {"median": 25.0, "min": 20.0, "max": 30.0, "count": 5}}
        with patch("scripts.genre_tracker.fetch_market_stats", return_value=stats):
            result = run_genre_tracker()
        assert result == 0

    def test_records_prices_on_success(self, _mock_db):
        stats = {"joe abercrombie hardback": {"median": 25.0, "min": 20.0, "max": 30.0, "count": 5}}
        with patch("scripts.genre_tracker.fetch_market_stats", return_value=stats):
            run_genre_tracker()
        _mock_db.assert_called_once()
