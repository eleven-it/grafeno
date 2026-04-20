"""
SQLAlchemy ORM models. Todas las entidades del dominio central.
UUID como PK en toda la app para facilitar distribución y ULID ordering.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, JSON,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lists: Mapped[list["ShoppingList"]] = relationship("ShoppingList", back_populates="user")


class ShoppingList(Base):
    __tablename__ = "shopping_lists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    list_type: Mapped[str] = mapped_column(String(32), nullable=False, default="recurrent")
    country: Mapped[str] = mapped_column(String(4), nullable=False, default="AR")
    currency: Mapped[str] = mapped_column(String(4), nullable=False, default="ARS")
    budget: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    monitoring_frequency: Mapped[str] = mapped_column(String(16), nullable=False, default="daily")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="lists")
    items: Mapped[list["ShoppingListItem"]] = relationship("ShoppingListItem", back_populates="list")


class ProductCanonical(Base):
    """
    Producto normalizado, independiente de la fuente.
    Actúa como anchor para agrupar ofertas equivalentes.
    """
    __tablename__ = "product_canonicals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    base_unit: Mapped[str] = mapped_column(String(8), nullable=False)  # L, kg, unit, m, m2, m3
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["ShoppingListItem"]] = relationship(
        "ShoppingListItem", back_populates="canonical_product"
    )
    offers: Mapped[list["OfferObservation"]] = relationship(
        "OfferObservation", back_populates="canonical_product"
    )


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    list_id: Mapped[str] = mapped_column(String(36), ForeignKey("shopping_lists.id"), nullable=False)
    canonical_product_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("product_canonicals.id"), nullable=True
    )

    # Input del usuario
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    preferred_brand: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    excluded_brands: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    desired_presentation: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    desired_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    allowed_stores: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    excluded_stores: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    allow_equivalents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allow_bulk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    list: Mapped["ShoppingList"] = relationship("ShoppingList", back_populates="items")
    canonical_product: Mapped[Optional["ProductCanonical"]] = relationship(
        "ProductCanonical", back_populates="items"
    )
    offers: Mapped[list["OfferObservation"]] = relationship(
        "OfferObservation", back_populates="item"
    )
    alert_rules: Mapped[list["AlertRule"]] = relationship("AlertRule", back_populates="item")


class OfferObservation(Base):
    """
    Captura de precio observado desde una fuente externa.
    Incluye datos de unit economics derivados en el momento de ingesta.
    """
    __tablename__ = "offer_observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("shopping_list_items.id"), nullable=True
    )
    canonical_product_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("product_canonicals.id"), nullable=True
    )

    # Datos de la fuente
    source: Mapped[str] = mapped_column(String(64), nullable=False)       # carrefour, walmart, etc.
    retailer: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="supermarket")
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_sku: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detected_brand: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    detected_category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Precio
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    original_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(4), nullable=False, default="ARS")
    in_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    shipping_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    promo_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    installments: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    seller: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Unit economics derivados en ingesta
    parsed_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    parsed_unit: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    parsed_pack_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    total_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    normalized_unit: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    price_per_base_unit: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4), nullable=True)

    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    matching_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(nullable=True)

    item: Mapped[Optional["ShoppingListItem"]] = relationship(
        "ShoppingListItem", back_populates="offers"
    )
    canonical_product: Mapped[Optional["ProductCanonical"]] = relationship(
        "ProductCanonical", back_populates="offers"
    )
    alert_events: Mapped[list["AlertEvent"]] = relationship("AlertEvent", back_populates="offer")


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    item_id: Mapped[str] = mapped_column(String(36), ForeignKey("shopping_list_items.id"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    threshold_unit: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)  # ARS, %, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    item: Mapped["ShoppingListItem"] = relationship("ShoppingListItem", back_populates="alert_rules")
    events: Mapped[list["AlertEvent"]] = relationship("AlertEvent", back_populates="rule")


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    rule_id: Mapped[str] = mapped_column(String(36), ForeignKey("alert_rules.id"), nullable=False)
    offer_id: Mapped[str] = mapped_column(String(36), ForeignKey("offer_observations.id"), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    rule: Mapped["AlertRule"] = relationship("AlertRule", back_populates="events")
    offer: Mapped["OfferObservation"] = relationship("OfferObservation", back_populates="alert_events")
