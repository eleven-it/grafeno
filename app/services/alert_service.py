"""
Motor de alertas. Evalúa reglas contra las últimas ofertas y genera eventos.
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models import AlertRule, AlertEvent, OfferObservation, ShoppingListItem
from app.services import offer_service
import uuid


def create_rule(db: Session, item_id: str, data: dict) -> AlertRule:
    rule = AlertRule(
        id=str(uuid.uuid4()),
        item_id=item_id,
        rule_type=data["rule_type"],
        threshold_value=Decimal(str(data["threshold_value"])) if data.get("threshold_value") else None,
        threshold_unit=data.get("threshold_unit"),
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_rules(db: Session, item_id: Optional[str] = None) -> list[AlertRule]:
    q = db.query(AlertRule).filter_by(is_active=True)
    if item_id:
        q = q.filter_by(item_id=item_id)
    return q.all()


def get_events(db: Session, item_id: Optional[str] = None) -> list[AlertEvent]:
    if item_id:
        rule_ids = [r.id for r in db.query(AlertRule).filter_by(item_id=item_id).all()]
        return db.query(AlertEvent).filter(AlertEvent.rule_id.in_(rule_ids)).all()
    return db.query(AlertEvent).order_by(AlertEvent.triggered_at.desc()).limit(100).all()


def evaluate_rules_for_item(db: Session, item_id: str) -> list[AlertEvent]:
    """
    Evalúa todas las reglas activas para un item contra sus últimas ofertas.
    Genera AlertEvent para cada regla disparada.
    """
    rules = get_rules(db, item_id)
    if not rules:
        return []

    offers = offer_service.get_offers_for_item(db, item_id)
    if not offers:
        return []

    latest_offer = offers[0]
    events: list[AlertEvent] = []

    for rule in rules:
        event = _evaluate_rule(rule, latest_offer, offers)
        if event:
            db.add(event)
            events.append(event)

    if events:
        db.commit()

    return events


def _evaluate_rule(
    rule: AlertRule,
    latest_offer: OfferObservation,
    all_offers: list[OfferObservation],
) -> Optional[AlertEvent]:
    triggered = False
    message = ""

    if rule.rule_type == "price_below":
        if rule.threshold_value and latest_offer.price < rule.threshold_value:
            triggered = True
            message = (
                f"Precio bajó a {latest_offer.price} {latest_offer.currency} "
                f"(umbral: {rule.threshold_value}). Fuente: {latest_offer.source}"
            )

    elif rule.rule_type == "unit_price_below":
        if (
            rule.threshold_value
            and latest_offer.price_per_base_unit
            and latest_offer.price_per_base_unit < rule.threshold_value
        ):
            triggered = True
            message = (
                f"Precio unitario bajó a {latest_offer.price_per_base_unit}/"
                f"{latest_offer.normalized_unit} "
                f"(umbral: {rule.threshold_value}). Fuente: {latest_offer.source}"
            )

    elif rule.rule_type == "price_drop_pct":
        # Comparar con la oferta anterior del mismo source
        prev_offers = [
            o for o in all_offers
            if o.source == latest_offer.source and o.id != latest_offer.id
        ]
        if prev_offers and rule.threshold_value:
            prev_price = prev_offers[0].price
            if prev_price > 0:
                drop_pct = (prev_price - latest_offer.price) / prev_price * 100
                if drop_pct >= rule.threshold_value:
                    triggered = True
                    message = (
                        f"Precio bajó {drop_pct:.1f}% en {latest_offer.source} "
                        f"({prev_price} → {latest_offer.price} {latest_offer.currency})"
                    )

    elif rule.rule_type == "back_in_stock":
        if latest_offer.in_stock:
            prev_out = [
                o for o in all_offers
                if o.source == latest_offer.source
                and not o.in_stock
                and o.id != latest_offer.id
            ]
            if prev_out:
                triggered = True
                message = f"Volvió a haber stock en {latest_offer.source}: {latest_offer.title}"

    elif rule.rule_type == "better_equivalent":
        # Si hay equivalentes más baratos que el precio target
        if rule.threshold_value:
            cheaper = [
                o for o in all_offers
                if o.price < rule.threshold_value and o.in_stock
            ]
            if cheaper:
                best = min(cheaper, key=lambda o: o.price)
                triggered = True
                message = (
                    f"Encontrado equivalente más barato: {best.title} "
                    f"a {best.price} en {best.source}"
                )

    if not triggered:
        return None

    return AlertEvent(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        offer_id=latest_offer.id,
        message=message,
        acknowledged=False,
    )
