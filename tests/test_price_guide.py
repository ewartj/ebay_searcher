"""Tests for price_guide.py — validates data integrity of the guide itself."""
import ast
from pathlib import Path

import pytest

from price_guide import PRICE_GUIDE


class TestPriceGuideIntegrity:
    def test_no_duplicate_keys(self):
        """Parse the source file to catch duplicate dict keys Python silently allows."""
        source = Path(__file__).parent.parent / "price_guide.py"
        tree = ast.parse(source.read_text())

        # Find the PRICE_GUIDE dict literal in the AST
        keys = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "PRICE_GUIDE":
                        if isinstance(node.value, ast.Dict):
                            keys = [
                                k.s for k in node.value.keys
                                if isinstance(k, ast.Constant) and isinstance(k.s, str)
                            ]

        duplicates = [k for k in set(keys) if keys.count(k) > 1]
        assert duplicates == [], f"Duplicate keys in PRICE_GUIDE: {duplicates}"

    def test_all_keys_are_lowercase(self):
        for key in PRICE_GUIDE:
            assert key == key.lower(), f"Key not lowercase: {key!r}"

    def test_plain_float_values_are_positive(self):
        for key, entry in PRICE_GUIDE.items():
            if isinstance(entry, (int, float)):
                assert entry > 0, f"Non-positive price for {key!r}: {entry}"

    def test_dict_values_contain_at_least_one_price(self):
        for key, entry in PRICE_GUIDE.items():
            if isinstance(entry, dict):
                assert entry, f"Empty dict entry for {key!r}"
                for fmt, price in entry.items():
                    assert fmt in ("hardback", "paperback"), (
                        f"Unknown format key {fmt!r} for {key!r}"
                    )
                    assert isinstance(price, (int, float)) and price > 0, (
                        f"Invalid price {price!r} for {key!r}[{fmt!r}]"
                    )

    def test_guide_is_not_empty(self):
        assert len(PRICE_GUIDE) > 50, "Price guide looks unexpectedly small"

    @pytest.mark.parametrize("title", [
        "horus rising",
        "saturnine",
        "eisenhorn",
        "soul hunter",
        "master of mankind",
    ])
    def test_known_titles_present(self, title):
        assert title in PRICE_GUIDE, f"{title!r} missing from price guide"
