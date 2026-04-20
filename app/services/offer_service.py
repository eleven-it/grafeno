"""
Servicio de ingesta y consulta de ofertas observadas.
Al importar una oferta se calculan automáticamente los unit economics.
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models import OfferObservation, ShoppingListItem
from app.services.unit_economics import calculate_unit_economics
from app.services.matching import match_score
import uuid


def import_offer(db: Session, data: dict) -> OfferObservation:
    """
    Importa una oferta desde cualquier fuente (mock, scraper, etc.)
    y deriva automáticamente los campos de unit economics.
    """
    price = Decimal(str(data["price"]))
    original_price = Decimal(str(data["original_price"])) if data.get("original_price") else None
    title = data["title"]

    ue = calculate_unit_economics(
        price=price,
        title=title,
        currency=data.get("currency", "ARS"),
        original_price=original_price,
        promo_description=data.get("promo_description"),
    )

    offer = OfferObservation(
        id=str(uuid.uuid4()),
        item_id=data.get("item_id"),
        canonical_product_id=data.get("canonical_product_id"),
        source=data["source"],
        retailer=data.get("retailer", data["source"]),
        source_type=data.get("source_type", "supermarket"),
        url=data.get("url"),
        external_sku=data.get("external_sku"),
        title=title,
        detected_brand=data.get("detected_brand"),
        detected_category=data.get("detected_category"),
        price=price,
        original_price=original_price,
        currency=data.get("currency", "ARS"),
        in_stock=data.get("in_stock", True),
        shipping_cost=Decimal(str(data["shipping_cost"])) if data.get("shipping_cost") else None,
        promo_description=data.get("promo_description"),
        installments=data.get("installments"),
        seller=data.get("seller"),
        raw_attributes=data.get("raw_attributes", {}),
        image_url=data.get("image_url"),
        # Unit economics
        parsed_quantity=ue.presentation.quantity if ue else None,
        parsed_unit=ue.presentation.raw_unit if ue else None,
        parsed_pack_size=ue.presentation.pack_size if ue else 1,
        total_quantity=ue.presentation.total_quantity if ue else None,
        normalized_unit=ue.base_unit if ue else None,
        price_per_base_unit=ue.price_per_base_unit if ue else None,
        matching_score=data.get("matching_score"),
        confidence_score=data.get("confidence_score"),
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def import_offers_batch(db: Session, offers: list[dict]) -> list[OfferObservation]:
    return [import_offer(db, o) for o in offers]


def get_offers_for_item(db: Session, item_id: str) -> list[OfferObservation]:
    return (
        db.query(OfferObservation)
        .filter_by(item_id=item_id)
        .order_by(OfferObservation.captured_at.desc())
        .all()
    )


def get_comparable_offers(
    db: Session,
    item_id: str,
    allow_equivalents: bool = True,
) -> list[OfferObservation]:
    """
    Retorna ofertas comparables para un item.
    Si allow_equivalents=True, busca por canonical_product_id también.
    """
    item: Optional[ShoppingListItem] = (
        db.query(ShoppingListItem).filter_by(id=item_id).first()
    )
    if not item:
        return []

    query = db.query(OfferObservation)

    if allow_equivalents and item.canonical_product_id:
        query = query.filter(
            (OfferObservation.item_id == item_id)
            | (OfferObservation.canonical_product_id == item.canonical_product_id)
        )
    else:
        query = query.filter_by(item_id=item_id)

    return query.order_by(OfferObservation.price_per_base_unit.asc().nullslast()).all()
