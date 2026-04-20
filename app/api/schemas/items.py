from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ShoppingListItemCreate(BaseModel):
    original_text: str = Field(..., min_length=1)
    category: Optional[str] = None
    preferred_brand: Optional[str] = None
    excluded_brands: Optional[list[str]] = None
    desired_presentation: Optional[str] = None
    desired_quantity: int = 1
    target_price: Optional[Decimal] = None
    priority: str = "medium"
    allowed_stores: Optional[list[str]] = None
    excluded_stores: Optional[list[str]] = None
    allow_equivalents: bool = True
    allow_bulk: bool = True


class ShoppingListItemUpdate(BaseModel):
    original_text: Optional[str] = None
    category: Optional[str] = None
    preferred_brand: Optional[str] = None
    excluded_brands: Optional[list[str]] = None
    desired_presentation: Optional[str] = None
    desired_quantity: Optional[int] = None
    target_price: Optional[Decimal] = None
    priority: Optional[str] = None
    allowed_stores: Optional[list[str]] = None
    excluded_stores: Optional[list[str]] = None
    allow_equivalents: Optional[bool] = None
    allow_bulk: Optional[bool] = None
    status: Optional[str] = None


class ShoppingListItemOut(BaseModel):
    id: str
    list_id: str
    original_text: str
    category: Optional[str]
    preferred_brand: Optional[str]
    excluded_brands: Optional[list[str]]
    desired_presentation: Optional[str]
    desired_quantity: int
    target_price: Optional[Decimal]
    priority: str
    allowed_stores: Optional[list[str]]
    excluded_stores: Optional[list[str]]
    allow_equivalents: bool
    allow_bulk: bool
    status: str
    canonical_product_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
