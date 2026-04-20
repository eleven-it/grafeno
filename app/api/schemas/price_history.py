from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class PricePointOut(BaseModel):
    captured_at: datetime
    source: str
    price: Decimal
    price_per_base_unit: Optional[Decimal]
    normalized_unit: Optional[str]
    in_stock: bool
    promo_description: Optional[str]


class PriceSeriesOut(BaseModel):
    source: str
    points: list[PricePointOut]
    min_price: Decimal
    max_price: Decimal
    latest_price: Decimal
    price_change_pct: Optional[Decimal]


class PriceHistoryOut(BaseModel):
    item_id: str
    base_unit: Optional[str]
    series: list[PriceSeriesOut]
    overall_min: Decimal
    overall_max: Decimal
    best_current_price: Optional[Decimal]
    best_current_source: Optional[str]
