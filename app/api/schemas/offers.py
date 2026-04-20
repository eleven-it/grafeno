from decimal import Decimal
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel


class OfferImport(BaseModel):
    """Payload para importar una oferta desde cualquier fuente."""
    item_id: Optional[str] = None
    canonical_product_id: Optional[str] = None
    source: str                          # "carrefour", "walmart", "mercadolibre", etc.
    retailer: Optional[str] = None
    source_type: str = "supermarket"     # supermarket | retail | marketplace
    url: Optional[str] = None
    external_sku: Optional[str] = None
    title: str
    detected_brand: Optional[str] = None
    detected_category: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    currency: str = "ARS"
    in_stock: bool = True
    shipping_cost: Optional[Decimal] = None
    promo_description: Optional[str] = None
    installments: Optional[dict] = None
    seller: Optional[str] = None
    raw_attributes: dict = {}
    image_url: Optional[str] = None
    matching_score: Optional[float] = None
    confidence_score: Optional[float] = None


class OfferBatchImport(BaseModel):
    offers: list[OfferImport]


class OfferOut(BaseModel):
    id: str
    item_id: Optional[str]
    canonical_product_id: Optional[str]
    source: str
    retailer: str
    source_type: str
    url: Optional[str]
    external_sku: Optional[str]
    title: str
    detected_brand: Optional[str]
    detected_category: Optional[str]
    price: Decimal
    original_price: Optional[Decimal]
    currency: str
    in_stock: bool
    shipping_cost: Optional[Decimal]
    promo_description: Optional[str]
    seller: Optional[str]
    image_url: Optional[str]
    # Unit economics
    parsed_quantity: Optional[Decimal]
    parsed_unit: Optional[str]
    parsed_pack_size: Optional[int]
    total_quantity: Optional[Decimal]
    normalized_unit: Optional[str]
    price_per_base_unit: Optional[Decimal]
    captured_at: datetime
    matching_score: Optional[float]
    confidence_score: Optional[float]

    model_config = {"from_attributes": True}


class UnitEconomicsOut(BaseModel):
    offer_id: str
    title: str
    price: Decimal
    currency: str
    parsed_quantity: Optional[Decimal]
    parsed_unit: Optional[str]
    pack_size: Optional[int]
    total_quantity: Optional[Decimal]
    base_unit: Optional[str]
    price_per_base_unit: Optional[Decimal]
    label: str   # human-readable: "$1100/L"
