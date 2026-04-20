"""
Motor de recomendaciones. Consume unit economics y genera sugerencias
interpretables para el usuario (y para un agente conversacional).

Separa claramente:
  - best_unit_value: menor precio por unidad base
  - best_total_price: menor desembolso
  - best_practical_choice: equilibrio razonable
"""
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models import OfferObservation, ShoppingListItem, ShoppingList
from app.services.unit_economics import calculate_unit_economics, compare_presentations
from app.services import offer_service


@dataclass
class OfferRecommendation:
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


@dataclass
class ItemRecommendation:
    item_id: str
    item_text: str
    best_unit_value: Optional[OfferRecommendation]
    best_total_price: Optional[OfferRecommendation]
    best_practical_choice: Optional[OfferRecommendation]
    savings_vs_worst_pct: Optional[Decimal]
    all_offers_count: int
    comparable_offers_count: int


@dataclass
class CartRecommendation:
    list_id: str
    list_name: str
    items: list[ItemRecommendation]
    total_best_unit: Decimal
    total_best_price: Decimal
    currency: str
    best_store_split: list[dict]   # [{"store": ..., "items": [...], "subtotal": ...}]


def _offer_to_dict(o: OfferObservation) -> dict:
    return {
        "offer_id": o.id,
        "title": o.title,
        "source": o.source,
        "price": float(o.price),
        "currency": o.currency,
        "original_price": float(o.original_price) if o.original_price else None,
        "promo_description": o.promo_description,
        "in_stock": o.in_stock,
    }


def recommend_item(db: Session, item_id: str) -> Optional[ItemRecommendation]:
    item: Optional[ShoppingListItem] = (
        db.query(ShoppingListItem).filter_by(id=item_id).first()
    )
    if not item:
        return None

    offers = offer_service.get_comparable_offers(
        db, item_id, allow_equivalents=item.allow_equivalents
    )
    if not offers:
        return ItemRecommendation(
            item_id=item_id,
            item_text=item.original_text,
            best_unit_value=None,
            best_total_price=None,
            best_practical_choice=None,
            savings_vs_worst_pct=None,
            all_offers_count=0,
            comparable_offers_count=0,
        )

    offer_dicts = [_offer_to_dict(o) for o in offers]
    comparison = compare_presentations(offer_dicts)

    def _to_rec(p, reasoning: str) -> Optional[OfferRecommendation]:
        if p is None:
            return None
        return OfferRecommendation(
            offer_id=p.offer_id,
            title=p.title,
            source=p.source,
            price=p.price,
            currency=p.currency,
            price_per_base_unit=p.effective_price_per_base_unit,
            base_unit=p.base_unit,
            total_in_base=p.total_in_base,
            in_stock=p.in_stock,
            reasoning=reasoning,
        )

    if comparison:
        best_uv = _to_rec(
            comparison.best_unit_value,
            f"Menor precio por {comparison.base_unit}: "
            f"{comparison.best_unit_value.effective_price_per_base_unit}/{comparison.base_unit}"
            if comparison.best_unit_value else "",
        )
        best_tp = _to_rec(
            comparison.best_total_price,
            f"Menor desembolso total: {comparison.best_total_price.price} {comparison.best_total_price.currency}"
            if comparison.best_total_price else "",
        )
        best_pc = _to_rec(
            comparison.best_practical_choice,
            "Mejor equilibrio entre precio y practicidad",
        )
        savings = comparison.savings_vs_worst
    else:
        # Solo una oferta
        o = offers[0]
        single = OfferRecommendation(
            offer_id=o.id,
            title=o.title,
            source=o.source,
            price=o.price,
            currency=o.currency,
            price_per_base_unit=o.price_per_base_unit,
            base_unit=o.normalized_unit,
            total_in_base=o.total_quantity,
            in_stock=o.in_stock,
            reasoning="Única oferta disponible",
        )
        best_uv = best_tp = best_pc = single
        savings = None

    return ItemRecommendation(
        item_id=item_id,
        item_text=item.original_text,
        best_unit_value=best_uv,
        best_total_price=best_tp,
        best_practical_choice=best_pc,
        savings_vs_worst_pct=savings,
        all_offers_count=len(offers),
        comparable_offers_count=len(comparison.presentations) if comparison else 1,
    )


def recommend_cart(db: Session, list_id: str) -> Optional[CartRecommendation]:
    """
    Para una lista completa, recomienda dónde comprar cada item
    y calcula la mejor división entre tiendas.
    """
    lst: Optional[ShoppingList] = db.query(ShoppingList).filter_by(id=list_id).first()
    if not lst:
        return None

    items_recs: list[ItemRecommendation] = []
    for item in lst.items:
        if item.status != "active":
            continue
        rec = recommend_item(db, item.id)
        if rec:
            items_recs.append(rec)

    total_best_unit = Decimal("0")
    total_best_price = Decimal("0")

    # Agrupar por tienda (best_practical_choice)
    store_map: dict[str, list] = {}
    for rec in items_recs:
        choice = rec.best_practical_choice
        if choice:
            total_best_price += choice.price * 1  # qty=1 por ahora
            if choice.price_per_base_unit and choice.total_in_base:
                total_best_unit += choice.price
            store_map.setdefault(choice.source, []).append({
                "item_id": rec.item_id,
                "item_text": rec.item_text,
                "offer_id": choice.offer_id,
                "price": float(choice.price),
            })

    store_split = [
        {
            "store": store,
            "items": items,
            "subtotal": sum(i["price"] for i in items),
        }
        for store, items in sorted(
            store_map.items(), key=lambda x: -sum(i["price"] for i in x[1])
        )
    ]

    return CartRecommendation(
        list_id=list_id,
        list_name=lst.name,
        items=items_recs,
        total_best_unit=total_best_unit,
        total_best_price=total_best_price,
        currency=lst.currency,
        best_store_split=store_split,
    )
