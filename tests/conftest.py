"""
Test configuration — sets fake env vars before any project modules are imported.
config.py reads credentials at module level, so these must be set first.
"""
import os

# Override with test values so no real API calls are made accidentally
os.environ["EBAY_CLIENT_ID"] = "test_ebay_client_id"
os.environ["EBAY_CLIENT_SECRET"] = "test_ebay_client_secret"
os.environ["ANTHROPIC_API_KEY"] = "test_anthropic_key"
os.environ["TELEGRAM_BOT_TOKEN"] = "1234567890:test_bot_token_AAA"
os.environ["TELEGRAM_CHAT_ID"] = "123456789"

import pytest
from unittest.mock import MagicMock

from models import Bargain, Listing


@pytest.fixture
def sample_listing():
    return Listing(
        title="Horus Rising Hardback",
        price_gbp=15.0,
        url="https://www.ebay.co.uk/itm/123",
        source="ebay",
    )


@pytest.fixture
def sample_bargain(sample_listing):
    return Bargain(
        listing=sample_listing,
        market_price=30.0,
        discount_pct=0.5,
        price_source="price_guide",
    )


def make_claude_mock(response_text: str) -> MagicMock:
    """Return a mock anthropic.Anthropic client that responds with response_text."""
    mock = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    mock.messages.create.return_value = msg
    return mock
