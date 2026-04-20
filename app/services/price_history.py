"""
Historial de precios derivado de OfferObservation.
No requiere tabla adicional — se construye agrupando observaciones.
"""
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.domain.models import OfferObservation


@dataclass
class PricePoint:
    captured_at: datetime
    source: str
    price: Decimal
    price_per_base_unit: Optional[Decimal]
    normalized_unit: Optional[str]
    in_stock: bool
    promo_description: Optional[str]


@dataclass
class PriceSeries:
    source: str
    points: list[PricePoint]
    min_price: Decimal
    max_price: Decimal
    latest_price: Decimal
    price_change_pct: Optional[Decimal]  # vs primera observación


@dataclass
class PriceHistory:
    item_id: str
    base_unit: Optional[str]
    series: list[PriceSeries]           # una serie por fuente
    overall_min: Decimal
    overall_max: Decimal
    best_current_price: Optional[Decimal]
    best_current_source: Optional[str]


def get_price_history(
    db: Session,
    item_id: str,
    days: int = 30,
    canonical_product_id: Optional[str] = None,
) -> Optional[PriceHistory]:
    """
    Retorna el historial de precios para un item (y opcionalmente sus equivalentes).
    """
    since = datetime.utcnow() - timedelta(days=days)

    query = db.query(OfferObservation).filter(
        OfferObservation.captured_at >= since
    )

    if canonical_product_id:
        query = query.filter(
            (OfferObservation.item_id == item_id)
            | (OfferObservation.canonical_product_id == canonical_product_id)
        )
    else:
        query = query.filter(OfferObservation.item_id == item_id)

    observations: list[OfferObservation] = (
        query.order_by(OfferObservation.captured_at.asc()).all()
    )

    if not observations:
        return None

    # Agrupar por source
    by_source: dict[str, list[OfferObservation]] = {}
    for obs in observations:
        by_source.setdefault(obs.source, []).append(obs)

    series: list[PriceSeries] = []
    all_prices: list[Decimal] = []

    for source, obs_list in sorted(by_source.items()):
        points = [
            PricePoint(
                captured_at=o.captured_at,
                source=o.source,
                price=o.price,
                price_per_base_unit=o.price_per_base_unit,
                normalized_unit=o.normalized_unit,
                in_stock=o.in_stock,
                promo_description=o.promo_description,
            )
            for o in obs_list
        ]
        prices = [p.price for p in points]
        all_prices.extend(prices)

        first_price = prices[0]
        last_price = prices[-1]
        change_pct = None
        if first_price > 0 and len(prices) > 1:
            change_pct = ((last_price - first_price) / first_price * 100).quantize(Decimal("0.1"))

        series.append(PriceSeries(
            source=source,
            points=points,
            min_price=min(prices),
            max_price=max(prices),
            latest_price=last_price,
            price_change_pct=change_pct,
        ))

    # Mejor precio actual (última observación por source, con stock)
    latest_by_source = {s: s_data.points[-1] for s, s_data in zip(by_source.keys(), series)}
    in_stock_latest = [(src, pt) for src, pt in latest_by_source.items() if pt.in_stock]

    best_source = None
    best_price = None
    if in_stock_latest:
        best_source, best_pt = min(in_stock_latest, key=lambda x: x[1].price)
        best_price = best_pt.price

    # Unidad base dominante
    units = [o.normalized_unit for o in observations if o.normalized_unit]
    base_unit = max(set(units), key=units.count) if units else None

    return PriceHistory(
        item_id=item_id,
        base_unit=base_unit,
        series=series,
        overall_min=min(all_prices),
        overall_max=max(all_prices),
        best_current_price=best_price,
        best_current_source=best_source,
    )
