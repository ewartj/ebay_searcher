"""Shared data models."""
from dataclasses import dataclass, field


@dataclass
class Listing:
    title: str
    price_gbp: float
    url: str
    source: str          # "ebay" | "vinted"
    condition: str | None = None
    image_url: str | None = None


@dataclass
class Bargain:
    listing: Listing
    market_price: float
    discount_pct: float  # 0.35 = 35% below market
    price_source: str    # "price_guide" | "ebay_sold" | "claude_estimate"
