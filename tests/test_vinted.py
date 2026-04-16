"""Tests for sources/vinted.py."""
import pytest

from sources.vinted import _parse_price


class TestParsePrice:
    def test_plain_string_price(self):
        assert _parse_price("12.99") == pytest.approx(12.99)

    def test_plain_float_price(self):
        assert _parse_price(12.99) == pytest.approx(12.99)

    def test_plain_int_price(self):
        assert _parse_price(10) == pytest.approx(10.0)

    def test_dict_gbp_price(self):
        assert _parse_price({"amount": "12.99", "currency_code": "GBP"}) == pytest.approx(12.99)

    def test_dict_non_gbp_returns_none(self):
        assert _parse_price({"amount": "12.99", "currency_code": "EUR"}) is None

    def test_dict_defaults_to_gbp_when_currency_missing(self):
        assert _parse_price({"amount": "5.00"}) == pytest.approx(5.0)

    def test_zero_returns_none(self):
        assert _parse_price(0) is None
        assert _parse_price("0") is None
        assert _parse_price({"amount": "0", "currency_code": "GBP"}) is None

    def test_negative_returns_none(self):
        assert _parse_price(-1.0) is None

    def test_invalid_string_returns_none(self):
        assert _parse_price("free") is None

    def test_none_returns_none(self):
        assert _parse_price(None) is None
