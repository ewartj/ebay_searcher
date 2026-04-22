"""Shared data models."""
from dataclasses import dataclass
from typing import Literal

# Valid values for Bargain.price_source
PriceSource = Literal["price_guide", "ebay_active", "claude_estimate"]


@dataclass
class Listing:
    title: str
    price_gbp: float
    url: str
    source: str          # "ebay" | "vinted" — must match a key in sources.SOURCES
    condition: str | None = None
    image_url: str | None = None
    is_bundle: bool = False
    category: str = "warhammer"  # "warhammer" | "fantasy"


@dataclass
class Bargain:
    listing: Listing
    market_price: float
    discount_pct: float  # 0.35 = 35% below market
    price_source: PriceSource
