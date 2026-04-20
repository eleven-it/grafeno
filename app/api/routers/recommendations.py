from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.recommendations import CartRecommendationOut, StoreSplitOut, CartItemOut
from app.services import recommendation as rec_service

router = APIRouter(tags=["recommendations"])


@router.get("/lists/{list_id}/best-cart", response_model=CartRecommendationOut)
def get_best_cart(list_id: str, db: Session = Depends(get_db)):
    cart = rec_service.recommend_cart(db, list_id)
    if not cart:
        raise HTTPException(status_code=404, detail="List not found")

    items_out = []
    for item_rec in cart.items:
        from app.api.schemas.recommendations import ItemRecommendationOut, OfferRecOut
        def _map_offer(o):
            if o is None:
                return None
            return OfferRecOut(
                offer_id=o.offer_id,
                title=o.title,
                source=o.source,
                price=o.price,
                currency=o.currency,
                price_per_base_unit=o.price_per_base_unit,
                base_unit=o.base_unit,
                total_in_base=o.total_in_base,
                in_stock=o.in_stock,
                reasoning=o.reasoning,
            )
        items_out.append(ItemRecommendationOut(
            item_id=item_rec.item_id,
            item_text=item_rec.item_text,
            best_unit_value=_map_offer(item_rec.best_unit_value),
            best_total_price=_map_offer(item_rec.best_total_price),
            best_practical_choice=_map_offer(item_rec.best_practical_choice),
            savings_vs_worst_pct=item_rec.savings_vs_worst_pct,
            all_offers_count=item_rec.all_offers_count,
            comparable_offers_count=item_rec.comparable_offers_count,
        ))

    store_split_out = []
    for split in cart.best_store_split:
        store_split_out.append(StoreSplitOut(
            store=split["store"],
            items=[CartItemOut(**i) for i in split["items"]],
            subtotal=split["subtotal"],
        ))

    return CartRecommendationOut(
        list_id=cart.list_id,
        list_name=cart.list_name,
        items=items_out,
        total_best_price=cart.total_best_price,
        currency=cart.currency,
        best_store_split=store_split_out,
    )
