"""Tests for sources/ebay_sold.py."""
import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from sources.ebay_sold import _clean_keywords, _trimmed_median, fetch_sold_stats


# ---------------------------------------------------------------------------
# _clean_keywords
# ---------------------------------------------------------------------------

class TestCleanKeywords:
    def test_strips_colon(self):
        assert ":" not in _clean_keywords("Eisenhorn: Omnibus")

    def test_strips_slash(self):
        assert "/" not in _clean_keywords("Black/White")

    def test_strips_hash(self):
        assert "#" not in _clean_keywords("Item #BC123")

    def test_strips_parens(self):
        result = _clean_keywords("Title (Hardback)")
        assert "(" not in result and ")" not in result

    def test_truncates_to_80_chars(self):
        assert len(_clean_keywords("word " * 30)) <= 80

    def test_truncates_at_word_boundary(self):
        result = _clean_keywords("word " * 30)
        assert not result.endswith(" ")

    def test_short_clean_title_unchanged(self):
        assert _clean_keywords("Horus Rising Hardback") == "Horus Rising Hardback"

    def test_collapses_whitespace(self):
        result = _clean_keywords("one  :  two")
        assert "  " not in result


# ---------------------------------------------------------------------------
# _trimmed_median
# ---------------------------------------------------------------------------

class TestTrimmedMedian:
    def test_single_value(self):
        assert _trimmed_median([10.0]) == 10.0

    def test_symmetric_list(self):
        result = _trimmed_median([10, 20, 30, 40, 50])
        assert result == pytest.approx(30.0)

    def test_trims_outliers(self):
        prices = [1.0] + [30.0] * 18 + [999.0]
        result = _trimmed_median(prices)
        assert result == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# fetch_sold_stats — HTTP-level behaviour
# ---------------------------------------------------------------------------

def _make_response(items: list[dict], status: int = 200) -> MagicMock:
    payload = {
        "findCompletedItemsResponse": [{
            "searchResult": [{"item": items}]
        }]
    }
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock()
    return resp


def _sold_item(price: float, currency: str = "GBP") -> dict:
    return {
        "sellingStatus": [{
            "sellingState": [{"__value__": "EndedWithSales"}],
            "currentPrice": [{"@currencyId": currency, "__value__": str(price)}],
        }]
    }


def _unsold_item(price: float) -> dict:
    return {
        "sellingStatus": [{
            "sellingState": [{"__value__": "EndedWithoutSales"}],
            "currentPrice": [{"@currencyId": "GBP", "__value__": str(price)}],
        }]
    }


class TestFetchSoldStats:
    def test_returns_median_for_sufficient_sales(self):
        items = [_sold_item(p) for p in [10, 20, 30, 40, 50]]
        with patch("sources.ebay_sold.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.get.return_value = _make_response(items)
            result = fetch_sold_stats(["some title"])
        assert "some title" in result
        assert result["some title"]["count"] == 5

    def test_ignores_unsold_items(self):
        items = [_sold_item(20), _sold_item(25), _sold_item(30), _unsold_item(5)]
        with patch("sources.ebay_sold.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.get.return_value = _make_response(items)
            result = fetch_sold_stats(["title"])
        assert result["title"]["count"] == 3

    def test_ignores_non_gbp(self):
        items = [_sold_item(20, "USD"), _sold_item(25, "GBP"), _sold_item(30, "GBP"), _sold_item(35, "GBP")]
        with patch("sources.ebay_sold.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.get.return_value = _make_response(items)
            result = fetch_sold_stats(["title"])
        assert result["title"]["count"] == 3

    def test_skips_title_with_fewer_than_min_sales(self):
        items = [_sold_item(20), _sold_item(25)]  # only 2, min is 3
        with patch("sources.ebay_sold.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.get.return_value = _make_response(items)
            result = fetch_sold_stats(["title"])
        assert "title" not in result

    def test_http_error_skips_title(self):
        with patch("sources.ebay_sold.httpx.Client") as mock_client_cls:
            mock = mock_client_cls.return_value.__enter__.return_value
            mock.get.side_effect = httpx.HTTPError("connection failed")
            result = fetch_sold_stats(["title"])
        assert result == {}

    def test_json_decode_error_skips_title(self):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.side_effect = json.JSONDecodeError("bad", "", 0)
        with patch("sources.ebay_sold.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.get.return_value = resp
            result = fetch_sold_stats(["title"])
        assert result == {}

    def test_deduplicates_titles(self):
        items = [_sold_item(p) for p in [10, 20, 30, 40, 50]]
        call_count = 0

        def fake_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_response(items)

        with patch("sources.ebay_sold.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.get.side_effect = fake_get
            fetch_sold_stats(["title", "title", "title"])
        assert call_count == 1
