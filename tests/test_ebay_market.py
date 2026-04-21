"""Tests for sources/ebay_market.py — trimmed median and market stats fetching."""
import statistics
from concurrent.futures import Future
from unittest.mock import MagicMock, patch

import pytest

from sources.ebay_market import (
    _MIN_LISTINGS,
    _trimmed_median,
    fetch_market_prices,
    fetch_market_stats,
)


# ---------------------------------------------------------------------------
# _trimmed_median
# ---------------------------------------------------------------------------

class TestTrimmedMedian:
    def test_single_value(self):
        assert _trimmed_median([10.0]) == 10.0

    def test_two_values(self):
        assert _trimmed_median([10.0, 20.0]) == pytest.approx(15.0)

    def test_all_equal(self):
        assert _trimmed_median([25.0, 25.0, 25.0, 25.0, 25.0]) == 25.0

    def test_trims_outliers(self):
        # 10 prices: trim=1, so [0.01] and [999.0] are removed
        prices = [0.01, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 999.0]
        result = _trimmed_median(prices)
        assert 20.0 < result < 30.0

    def test_small_list_falls_back_to_full(self):
        # n=3, trim=max(1,0)=1, 3 > 2*1 so trimmed=[prices[1]] → median of middle element
        # Actually n=3, trim=1 (max(1, 3//10)=max(1,0)=1), n > 2*trim (3>2) so trimmed=[20.0]
        prices = [10.0, 20.0, 30.0]
        result = _trimmed_median(prices)
        assert result == 20.0

    def test_returns_median_of_trimmed_range(self):
        # 20 prices, trim=2, trimmed = prices[2:18]
        prices = list(range(1, 21))  # 1..20
        expected = statistics.median(list(range(3, 19)))  # trim 2 each end
        assert _trimmed_median([float(p) for p in prices]) == pytest.approx(expected)

    def test_n_equals_2_times_trim_uses_full_list(self):
        # n=2, trim=max(1,0)=1, n > 2*trim is False (2 > 2 = False) → uses full list
        prices = [10.0, 30.0]
        assert _trimmed_median(prices) == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# fetch_market_stats — mocked eBay responses
# ---------------------------------------------------------------------------

def _make_ebay_response(prices_gbp: list[float]) -> MagicMock:
    items = [
        {"price": {"currency": "GBP", "value": str(p)}}
        for p in prices_gbp
    ]
    resp = MagicMock()
    resp.json.return_value = {"itemSummaries": items}
    resp.raise_for_status = MagicMock()
    return resp


def _make_client(response: MagicMock) -> MagicMock:
    client = MagicMock()
    client.get.return_value = response
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    return client


class TestFetchMarketStats:
    def test_empty_titles_returns_empty(self):
        assert fetch_market_stats([]) == {}

    def test_token_failure_returns_empty(self):
        with patch("sources.ebay_market.get_app_token", side_effect=Exception("auth fail")):
            with patch("sources.ebay_market.httpx.Client"):
                result = fetch_market_stats(["Horus Rising Hardback"])
        assert result == {}

    def test_returns_stats_for_title_with_enough_listings(self):
        prices = [30.0, 32.0, 28.0, 35.0, 31.0]
        resp = _make_ebay_response(prices)

        with patch("sources.ebay_market.get_app_token", return_value="tok"):
            with patch("sources.ebay_market.httpx.Client", return_value=_make_client(resp)):
                result = fetch_market_stats(["Horus Rising Hardback"])

        assert "Horus Rising Hardback" in result
        stats = result["Horus Rising Hardback"]
        assert stats["count"] == 5
        assert stats["min"] == 28.0
        assert stats["max"] == 35.0
        assert "median" in stats

    def test_skips_title_with_fewer_than_min_listings(self):
        resp = _make_ebay_response([20.0] * (_MIN_LISTINGS - 1))

        with patch("sources.ebay_market.get_app_token", return_value="tok"):
            with patch("sources.ebay_market.httpx.Client", return_value=_make_client(resp)):
                result = fetch_market_stats(["Obscure Title"])

        assert result == {}

    def test_skips_non_gbp_prices(self):
        resp = MagicMock()
        resp.json.return_value = {"itemSummaries": [
            {"price": {"currency": "USD", "value": "25.0"}},
            {"price": {"currency": "EUR", "value": "22.0"}},
        ]}
        resp.raise_for_status = MagicMock()

        with patch("sources.ebay_market.get_app_token", return_value="tok"):
            with patch("sources.ebay_market.httpx.Client", return_value=_make_client(resp)):
                result = fetch_market_stats(["Horus Rising Hardback"])

        assert result == {}

    def test_deduplicates_titles(self):
        resp = _make_ebay_response([30.0, 31.0, 32.0, 33.0, 34.0])
        call_count = {"n": 0}
        original_get = resp.get

        def counting_get(*args, **kwargs):
            call_count["n"] += 1
            return resp

        client = MagicMock()
        client.get.side_effect = counting_get
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)

        with patch("sources.ebay_market.get_app_token", return_value="tok"):
            with patch("sources.ebay_market.httpx.Client", return_value=client):
                fetch_market_stats(["Horus Rising", "Horus Rising"])

        assert call_count["n"] == 1

    def test_http_error_returns_none_for_that_title(self):
        import httpx

        resp = MagicMock()
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=MagicMock(status_code=404)
        )
        client = _make_client(resp)

        with patch("sources.ebay_market.get_app_token", return_value="tok"):
            with patch("sources.ebay_market.httpx.Client", return_value=client):
                result = fetch_market_stats(["Missing Title"])

        assert result == {}

    def test_connection_error_skips_title(self):
        import httpx

        client = MagicMock()
        client.get.side_effect = httpx.ConnectError("refused")
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)

        with patch("sources.ebay_market.get_app_token", return_value="tok"):
            with patch("sources.ebay_market.httpx.Client", return_value=client):
                result = fetch_market_stats(["Any Title"])

        assert result == {}

    def test_invalid_price_value_skipped(self):
        resp = MagicMock()
        resp.json.return_value = {"itemSummaries": [
            {"price": {"currency": "GBP", "value": "not_a_number"}},
            {"price": {"currency": "GBP", "value": "30.0"}},
            {"price": {"currency": "GBP", "value": "31.0"}},
            {"price": {"currency": "GBP", "value": "32.0"}},
        ]}
        resp.raise_for_status = MagicMock()

        with patch("sources.ebay_market.get_app_token", return_value="tok"):
            with patch("sources.ebay_market.httpx.Client", return_value=_make_client(resp)):
                result = fetch_market_stats(["Some Title"])

        assert "Some Title" in result
        assert result["Some Title"]["count"] == 3


# ---------------------------------------------------------------------------
# fetch_market_prices — convenience wrapper
# ---------------------------------------------------------------------------

class TestFetchMarketPrices:
    def test_returns_median_keyed_by_title(self):
        prices = [28.0, 30.0, 32.0, 34.0, 36.0]
        resp = _make_ebay_response(prices)

        with patch("sources.ebay_market.get_app_token", return_value="tok"):
            with patch("sources.ebay_market.httpx.Client", return_value=_make_client(resp)):
                result = fetch_market_prices(["Horus Rising Hardback"])

        assert "Horus Rising Hardback" in result
        assert isinstance(result["Horus Rising Hardback"], float)
