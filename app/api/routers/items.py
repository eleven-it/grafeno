from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.items import ShoppingListItemCreate, ShoppingListItemUpdate, ShoppingListItemOut
from app.api.schemas.offers import OfferOut, UnitEconomicsOut
from app.api.schemas.recommendations import ItemRecommendationOut
from app.services import item_service, list_service, offer_service, recommendation
from app.services.unit_economics import calculate_unit_economics
from decimal import Decimal

router = APIRouter(tags=["items"])


@router.post("/lists/{list_id}/items", response_model=ShoppingListItemOut, status_code=201)
def create_item(list_id: str, body: ShoppingListItemCreate, db: Session = Depends(get_db)):
    lst = list_service.get_list(db, list_id)
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    return item_service.create_item(db, list_id, body.model_dump())


@router.get("/lists/{list_id}/items", response_model=list[ShoppingListItemOut])
def get_items(list_id: str, db: Session = Depends(get_db)):
    lst = list_service.get_list(db, list_id)
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    return item_service.get_items_for_list(db, list_id)


@router.patch("/items/{item_id}", response_model=ShoppingListItemOut)
def update_item(item_id: str, body: ShoppingListItemUpdate, db: Session = Depends(get_db)):
    item = item_service.update_item(db, item_id, body.model_dump(exclude_none=True))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str, db: Session = Depends(get_db)):
    ok = item_service.delete_item(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")


@router.get("/items/{item_id}/offers", response_model=list[OfferOut])
def get_item_offers(item_id: str, db: Session = Depends(get_db)):
    item = item_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return offer_service.get_offers_for_item(db, item_id)


@router.get("/items/{item_id}/unit-economics", response_model=list[UnitEconomicsOut])
def get_unit_economics(item_id: str, db: Session = Depends(get_db)):
    item = item_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    offers = offer_service.get_comparable_offers(db, item_id, item.allow_equivalents)
    results = []
    for o in offers:
        ue = calculate_unit_economics(
            price=o.price,
            title=o.title,
            currency=o.currency,
            promo_description=o.promo_description,
        )
        label = (
            f"${o.price_per_base_unit:.2f}/{o.normalized_unit}"
            if o.price_per_base_unit and o.normalized_unit
            else "sin dato"
        )
        results.append(UnitEconomicsOut(
            offer_id=o.id,
            title=o.title,
            price=o.price,
            currency=o.currency,
            parsed_quantity=o.parsed_quantity,
            parsed_unit=o.parsed_unit,
            pack_size=o.parsed_pack_size,
            total_quantity=o.total_quantity,
            base_unit=o.normalized_unit,
            price_per_base_unit=o.price_per_base_unit,
            label=label,
        ))
    return results


@router.get("/items/{item_id}/comparisons", response_model=list[UnitEconomicsOut])
def get_comparisons(item_id: str, db: Session = Depends(get_db)):
    """Alias de unit-economics orientado a comparación entre presentaciones."""
    return get_unit_economics(item_id, db)


@router.get("/items/{item_id}/recommendation", response_model=ItemRecommendationOut)
def get_recommendation(item_id: str, db: Session = Depends(get_db)):
    item = item_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    rec = recommendation.recommend_item(db, item_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Item not found")
    return rec
