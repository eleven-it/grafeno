from typing import Optional
from pydantic import BaseModel


class SyncResultOut(BaseModel):
    item_id: str
    item_text: str
    connector: str
    offers_found: int
    offers_imported: int
    offers_skipped: int


class ListSyncSummaryOut(BaseModel):
    list_id: str
    items_synced: int
    total_offers_imported: int
    results: list[SyncResultOut]


class SearchResultOut(BaseModel):
    source: str
    retailer: str
    title: str
    price: float
    currency: str
    in_stock: bool
    detected_brand: Optional[str]
    detected_category: Optional[str]
    promo_description: Optional[str]
    url: Optional[str]
    external_sku: Optional[str]
