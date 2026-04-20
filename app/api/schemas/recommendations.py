from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class OfferRecOut(BaseModel):
    offer_id: str
    title: str
    source: str
    price: Decimal
    currency: str
    price_per_base_unit: Optional[Decimal]
    base_unit: Optional[str]
    total_in_base: Optional[Decimal]
    in_stock: bool
    reasoning: str


class ItemRecommendationOut(BaseModel):
    item_id: str
    item_text: str
    best_unit_value: Optional[OfferRecOut]
    best_total_price: Optional[OfferRecOut]
    best_practical_choice: Optional[OfferRecOut]
    savings_vs_worst_pct: Optional[Decimal]
    all_offers_count: int
    comparable_offers_count: int


class CartItemOut(BaseModel):
    item_id: str
    item_text: str
    offer_id: Optional[str]
    price: Optional[float]


class StoreSplitOut(BaseModel):
    store: str
    items: list[CartItemOut]
    subtotal: float


class CartRecommendationOut(BaseModel):
    list_id: str
    list_name: str
    items: list[ItemRecommendationOut]
    total_best_price: Decimal
    currency: str
    best_store_split: list[StoreSplitOut]
