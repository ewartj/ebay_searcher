"""Tests for sources/etsy.py."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from sources.etsy import _gbp_price, fetch_etsy_listings


# --- _gbp_price unit tests ---

class TestGbpPrice:
    def test_returns_gbp_price(self):
        assert _gbp_price({"currency_code": "GBP", "amount": 2500, "divisor": 100}) == pytest.approx(25.0)

    def test_returns_none_for_usd(self):
        assert _gbp_price({"currency_code": "USD", "amount": 2500, "divisor": 100}) is None

    def test_returns_none_for_zero(self):
        assert _gbp_price({"currency_code": "GBP", "amount": 0, "divisor": 100}) is None

    def test_returns_none_for_zero_divisor(self):
        assert _gbp_price({"currency_code": "GBP", "amount": 2500, "divisor": 0}) is None

    def test_defaults_divisor_to_100(self):
        assert _gbp_price({"currency_code": "GBP", "amount": 1000}) == pytest.approx(10.0)

    def test_returns_none_for_empty_dict(self):
        assert _gbp_price({}) is None

    def test_returns_none_for_missing_amount(self):
        assert _gbp_price({"currency_code": "GBP", "divisor": 100}) is None


# --- fetch_etsy_listings ---

def _make_response(items: list[dict]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"results": items}
    return resp


def _etsy_item(
    listing_id: int = 1001,
    title: str = "Black Library Hardback",
    amount: int = 2500,
    currency: str = "GBP",
    url: str = "https://www.etsy.com/listing/1001/",
) -> dict:
    return {
        "listing_id": listing_id,
        "title": title,
        "price": {"amount": amount, "divisor": 100, "currency_code": currency},
        "url": url,
        "images": [{"url_fullxfull": "https://i.etsy.com/img.jpg"}],
    }


class TestFetchEtsyListings:
    def test_skips_silently_when_no_api_key(self):
        with patch("sources.etsy.config.ETSY_API_KEY", ""):
            result = fetch_etsy_listings([("black library hardback", 10)])
        assert result == []

    def test_returns_gbp_listings(self):
        with patch("sources.etsy.config.ETSY_API_KEY", "test-key"), \
             patch("sources.etsy.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = _make_response([
                _etsy_item(listing_id=1, title="Horus Rising Hardback", amount=2000)
            ])
            results = fetch_etsy_listings([("horus rising hardback", 10)])
        assert len(results) == 1
        assert results[0].price_gbp == pytest.approx(20.0)
        assert results[0].source == "etsy"
        assert results[0].title == "Horus Rising Hardback"

    def test_skips_non_gbp(self):
        with patch("sources.etsy.config.ETSY_API_KEY", "test-key"), \
             patch("sources.etsy.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = _make_response([
                _etsy_item(listing_id=1, currency="USD"),
                _etsy_item(listing_id=2, currency="GBP"),
            ])
            results = fetch_etsy_listings([("hardback", 10)])
        assert len(results) == 1

    def test_deduplicates_by_listing_id(self):
        with patch("sources.etsy.config.ETSY_API_KEY", "test-key"), \
             patch("sources.etsy.httpx.Client") as mock_cls:
            item = _etsy_item(listing_id=999)
            mock = mock_cls.return_value.__enter__.return_value
            mock.get.return_value = _make_response([item, item])
            results = fetch_etsy_listings([("hardback", 10)])
        assert len(results) == 1

    def test_http_error_skips_term_continues(self):
        with patch("sources.etsy.config.ETSY_API_KEY", "test-key"), \
             patch("sources.etsy.httpx.Client") as mock_cls:
            mock = mock_cls.return_value.__enter__.return_value
            bad = MagicMock()
            bad.raise_for_status.side_effect = httpx.HTTPStatusError(
                "403", request=MagicMock(), response=MagicMock(status_code=403)
            )
            good = _make_response([_etsy_item(listing_id=5, title="Good Book")])

            call_count = 0
            def get_side(url, **kwargs):
                nonlocal call_count
                call_count += 1
                return bad if call_count == 1 else good

            mock.get.side_effect = get_side
            results = fetch_etsy_listings([("bad term", 10), ("good term", 10)])
        assert len(results) == 1

    def test_uses_default_search_terms_when_none_passed(self):
        fake_terms = [("test hardback", 5)]
        with patch("sources.etsy.config.ETSY_API_KEY", "test-key"), \
             patch("sources.etsy.config.ETSY_SEARCH_TERMS", fake_terms), \
             patch("sources.etsy.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = _make_response([])
            fetch_etsy_listings()  # no args
            call_args = mock_cls.return_value.__enter__.return_value.get.call_args
        assert call_args[1]["params"]["keywords"] == "test hardback"

    def test_category_set_on_listing(self):
        with patch("sources.etsy.config.ETSY_API_KEY", "test-key"), \
             patch("sources.etsy.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = _make_response([
                _etsy_item(listing_id=7)
            ])
            results = fetch_etsy_listings([("hardback", 10)], category="fantasy")
        assert results[0].category == "fantasy"

    def test_image_url_extracted(self):
        with patch("sources.etsy.config.ETSY_API_KEY", "test-key"), \
             patch("sources.etsy.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.return_value.get.return_value = _make_response([
                _etsy_item(listing_id=8)
            ])
            results = fetch_etsy_listings([("hardback", 10)])
        assert results[0].image_url == "https://i.etsy.com/img.jpg"
