"""Tests for the feedback loop — DB operations and Telegram polling."""
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

import config
import db
from db import (
    get_feedback_examples,
    get_last_alert_positions,
    get_previously_alerted_urls,
    get_setting,
    init_db,
    set_setting,
    store_alert_positions,
    store_feedback,
)
from models import Bargain, Listing
from notifier import poll_feedback


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    with patch.object(config, "DB_PATH", db_path):
        init_db()
        yield db_path


def _listing(url: str = "https://ebay.co.uk/1", title: str = "Some Book") -> Listing:
    return Listing(title=title, price_gbp=10.0, url=url, source="ebay")


def _bargain(url: str = "https://ebay.co.uk/1", title: str = "Some Book") -> Bargain:
    return Bargain(
        listing=_listing(url=url, title=title),
        market_price=30.0,
        discount_pct=0.67,
        price_source="price_guide",
    )


# ---------------------------------------------------------------------------
# store_alert_positions / get_last_alert_positions
# ---------------------------------------------------------------------------

class TestAlertPositions:
    def test_stores_and_retrieves_positions(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            bargains = [
                _bargain("https://ebay.co.uk/1", "Book A"),
                _bargain("https://ebay.co.uk/2", "Book B"),
            ]
            store_alert_positions(None, bargains, bot="wh")
            positions = get_last_alert_positions(bot="wh")

        assert positions[1] == ("https://ebay.co.uk/1", "Book A")
        assert positions[2] == ("https://ebay.co.uk/2", "Book B")

    def test_replaces_previous_positions_for_same_bot(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_alert_positions(None, [_bargain("https://ebay.co.uk/old", "Old")], bot="wh")
            store_alert_positions(None, [_bargain("https://ebay.co.uk/new", "New")], bot="wh")
            positions = get_last_alert_positions(bot="wh")

        assert len(positions) == 1
        assert positions[1][1] == "New"

    def test_separate_bots_are_independent(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_alert_positions(None, [_bargain("https://ebay.co.uk/wh", "WH Book")], bot="wh")
            store_alert_positions(None, [_bargain("https://ebay.co.uk/fa", "FA Book")], bot="fa")
            wh = get_last_alert_positions(bot="wh")
            fa = get_last_alert_positions(bot="fa")

        assert wh[1][1] == "WH Book"
        assert fa[1][1] == "FA Book"

    def test_empty_when_no_positions_stored(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            positions = get_last_alert_positions(bot="wh")
        assert positions == {}


# ---------------------------------------------------------------------------
# store_feedback / get_feedback_examples
# ---------------------------------------------------------------------------

class TestFeedback:
    def test_stores_good_outcome(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_feedback("https://ebay.co.uk/1", "Horus Rising", "good")
            examples = get_feedback_examples()
        assert "Horus Rising" in examples["good"]
        assert examples["bad"] == []

    def test_stores_bad_outcome(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_feedback("https://ebay.co.uk/1", "Warhammer Rulebook", "bad")
            examples = get_feedback_examples()
        assert "Warhammer Rulebook" in examples["bad"]
        assert examples["good"] == []

    def test_deduplicates_titles_in_examples(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_feedback("https://ebay.co.uk/1", "Same Book", "good")
            store_feedback("https://ebay.co.uk/2", "Same Book", "good")
            examples = get_feedback_examples()
        assert examples["good"].count("Same Book") == 1

    def test_respects_limit(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            for i in range(15):
                store_feedback(f"https://ebay.co.uk/{i}", f"Book {i}", "good")
            examples = get_feedback_examples(limit=5)
        assert len(examples["good"]) == 5


# ---------------------------------------------------------------------------
# get_previously_alerted_urls
# ---------------------------------------------------------------------------

class TestPreviouslyAlertedUrls:
    def test_returns_urls_in_alerted_listings(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            from db import record_alerted_urls
            record_alerted_urls(["https://ebay.co.uk/abc"])
            result = get_previously_alerted_urls(["https://ebay.co.uk/abc", "https://ebay.co.uk/new"])
        assert "https://ebay.co.uk/abc" in result
        assert "https://ebay.co.uk/new" not in result

    def test_returns_empty_set_for_empty_input(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            result = get_previously_alerted_urls([])
        assert result == set()


# ---------------------------------------------------------------------------
# settings
# ---------------------------------------------------------------------------

class TestSettings:
    def test_get_returns_default_when_unset(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            assert get_setting("missing_key", "42") == "42"

    def test_set_and_get_roundtrip(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            set_setting("my_key", "hello")
            assert get_setting("my_key") == "hello"

    def test_update_overwrites(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            set_setting("k", "first")
            set_setting("k", "second")
            assert get_setting("k") == "second"


# ---------------------------------------------------------------------------
# poll_feedback
# ---------------------------------------------------------------------------

def _make_update(update_id: int, chat_id: str, text: str) -> dict:
    return {
        "update_id": update_id,
        "message": {
            "chat": {"id": int(chat_id)},
            "text": text,
        },
    }


def _mock_getUpdates(updates: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"result": updates}
    return resp


class TestPollFeedback:
    def test_good_command_marks_all_items(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_alert_positions(None, [
                _bargain("https://ebay.co.uk/1", "Book A"),
                _bargain("https://ebay.co.uk/2", "Book B"),
            ], bot="wh")

            with patch("notifier.httpx.get") as mock_get:
                mock_get.return_value = _mock_getUpdates([
                    _make_update(1, "123456", "/good"),
                ])
                count = poll_feedback("token", "123456", bot="wh")

        assert count == 2

    def test_good_with_position_marks_specific_item(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_alert_positions(None, [
                _bargain("https://ebay.co.uk/1", "Book A"),
                _bargain("https://ebay.co.uk/2", "Book B"),
            ], bot="wh")

            with patch("notifier.httpx.get") as mock_get:
                mock_get.return_value = _mock_getUpdates([
                    _make_update(1, "123456", "/good 2"),
                ])
                count = poll_feedback("token", "123456", bot="wh")

        with patch.object(config, "DB_PATH", temp_db):
            examples = get_feedback_examples()
        assert count == 1
        assert "Book B" in examples["good"]
        assert "Book A" not in examples["good"]

    def test_bad_command_stores_bad_outcome(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_alert_positions(None, [_bargain("https://ebay.co.uk/1", "Junk")], bot="wh")

            with patch("notifier.httpx.get") as mock_get:
                mock_get.return_value = _mock_getUpdates([
                    _make_update(1, "123456", "/bad 1"),
                ])
                poll_feedback("token", "123456", bot="wh")
            examples = get_feedback_examples()

        assert "Junk" in examples["bad"]

    def test_ignores_messages_from_wrong_chat(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_alert_positions(None, [_bargain()], bot="wh")

            with patch("notifier.httpx.get") as mock_get:
                mock_get.return_value = _mock_getUpdates([
                    _make_update(1, "9999999", "/good"),
                ])
                count = poll_feedback("token", "123456", bot="wh")

        assert count == 0

    def test_advances_offset_after_processing(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_alert_positions(None, [_bargain()], bot="wh")

            with patch("notifier.httpx.get") as mock_get:
                mock_get.return_value = _mock_getUpdates([
                    _make_update(42, "123456", "/good 1"),
                ])
                poll_feedback("token", "123456", bot="wh")

            assert get_setting("tg_offset_wh") == "43"

    def test_returns_zero_on_http_error(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            with patch("notifier.httpx.get", side_effect=Exception("refused")):
                count = poll_feedback("token", "123456", bot="wh")
        assert count == 0

    def test_returns_zero_when_no_token(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            count = poll_feedback("", "123456", bot="wh")
        assert count == 0

    def test_comma_separated_positions(self, temp_db):
        with patch.object(config, "DB_PATH", temp_db):
            store_alert_positions(None, [
                _bargain("https://ebay.co.uk/1", "A"),
                _bargain("https://ebay.co.uk/2", "B"),
                _bargain("https://ebay.co.uk/3", "C"),
            ], bot="wh")

            with patch("notifier.httpx.get") as mock_get:
                mock_get.return_value = _mock_getUpdates([
                    _make_update(1, "123456", "/good 1,3"),
                ])
                count = poll_feedback("token", "123456", bot="wh")

        assert count == 2
