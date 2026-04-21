"""Tests for sources/ebay.py."""
from unittest.mock import MagicMock, patch

import pytest

from sources.ebay import fetch_ebay_listings


class TestFetchEbayListings:
    def _make_item(self, title="Horus Rising Hardback", price="15.00", item_id="1"):
        return {
            "itemId": item_id,
            "title": title,
            "price": {"value": price, "currency": "GBP"},
            "itemWebUrl": f"https://www.ebay.co.uk/itm/{item_id}",
            "condition": "Very Good",
            "image": {"imageUrl": "https://i.ebayimg.com/thumb.jpg"},
        }

    def _mock_response(self, items: list) -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = {"itemSummaries": items}
        resp.raise_for_status.return_value = None
        return resp

    def test_returns_listings(self):
        token_resp = MagicMock()
        token_resp.json.return_value = {"access_token": "tok", "expires_in": 7200}
        token_resp.raise_for_status.return_value = None

        search_resp = self._mock_response([self._make_item()])

        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = token_resp
        mock_client.get.return_value = search_resp

        with patch("sources.ebay.httpx.Client", return_value=mock_client):
            listings = fetch_ebay_listings()

        assert len(listings) >= 1
        assert listings[0].title == "Horus Rising Hardback"
        assert listings[0].price_gbp == pytest.approx(15.0)
        assert listings[0].source == "ebay"

    def test_non_gbp_items_excluded(self):
        item = self._make_item()
        item["price"]["currency"] = "USD"

        token_resp = MagicMock()
        token_resp.json.return_value = {"access_token": "tok", "expires_in": 7200}
        token_resp.raise_for_status.return_value = None

        search_resp = self._mock_response([item])

        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = token_resp
        mock_client.get.return_value = search_resp

        with patch("sources.ebay.httpx.Client", return_value=mock_client):
            listings = fetch_ebay_listings()

        assert listings == []

    def test_duplicate_items_deduplicated(self):
        items = [self._make_item(item_id="42"), self._make_item(item_id="42")]

        token_resp = MagicMock()
        token_resp.json.return_value = {"access_token": "tok", "expires_in": 7200}
        token_resp.raise_for_status.return_value = None

        search_resp = self._mock_response(items)

        mock_client = MagicMock()
        mock_client.__enter__ = lambda s: mock_client
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = token_resp
        mock_client.get.return_value = search_resp

        with patch("sources.ebay.httpx.Client", return_value=mock_client):
            listings = fetch_ebay_listings()

        ids = [l.url for l in listings]
        assert len(ids) == len(set(ids))
