from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class AlertRuleCreate(BaseModel):
    item_id: str
    rule_type: str   # price_below | price_drop_pct | back_in_stock | better_equivalent | unit_price_below
    threshold_value: Optional[Decimal] = None
    threshold_unit: Optional[str] = None  # ARS, USD, %


class AlertRuleOut(BaseModel):
    id: str
    item_id: str
    rule_type: str
    threshold_value: Optional[Decimal]
    threshold_unit: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertEventOut(BaseModel):
    id: str
    rule_id: str
    offer_id: str
    triggered_at: datetime
    message: str
    acknowledged: bool
    acknowledged_at: Optional[datetime]

    model_config = {"from_attributes": True}
