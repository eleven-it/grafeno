from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CanonicalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    category: str
    base_unit: str = "unit"     # L, kg, unit, m, m2, m3
    attributes: dict = {}


class CanonicalOut(BaseModel):
    id: str
    name: str
    category: str
    base_unit: str
    attributes: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LinkItemRequest(BaseModel):
    canonical_id: str
