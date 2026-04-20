from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.price_history import PriceHistoryOut, PriceSeriesOut, PricePointOut
from app.services import item_service, price_history as ph_service

router = APIRouter(tags=["price_history"])


@router.get("/items/{item_id}/price-history", response_model=PriceHistoryOut)
def get_price_history(
    item_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Historial de precios de un item agrupado por fuente.
    Muestra evolución de precios, mínimos, máximos y mejor precio actual.
    """
    item = item_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    history = ph_service.get_price_history(
        db, item_id, days=days,
        canonical_product_id=item.canonical_product_id,
    )

    if not history:
        raise HTTPException(status_code=404, detail="No price history found for this item")

    return PriceHistoryOut(
        item_id=history.item_id,
        base_unit=history.base_unit,
        series=[
            PriceSeriesOut(
                source=s.source,
                points=[
                    PricePointOut(
                        captured_at=p.captured_at,
                        source=p.source,
                        price=p.price,
                        price_per_base_unit=p.price_per_base_unit,
                        normalized_unit=p.normalized_unit,
                        in_stock=p.in_stock,
                        promo_description=p.promo_description,
                    )
                    for p in s.points
                ],
                min_price=s.min_price,
                max_price=s.max_price,
                latest_price=s.latest_price,
                price_change_pct=s.price_change_pct,
            )
            for s in history.series
        ],
        overall_min=history.overall_min,
        overall_max=history.overall_max,
        best_current_price=history.best_current_price,
        best_current_source=history.best_current_source,
    )
