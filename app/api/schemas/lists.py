from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ShoppingListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    list_type: str = "recurrent"
    country: str = "AR"
    currency: str = "ARS"
    budget: Optional[Decimal] = None
    monitoring_frequency: str = "daily"


class ShoppingListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    list_type: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    budget: Optional[Decimal] = None
    monitoring_frequency: Optional[str] = None
    status: Optional[str] = None


class ShoppingListOut(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str]
    list_type: str
    country: str
    currency: str
    budget: Optional[Decimal]
    monitoring_frequency: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
