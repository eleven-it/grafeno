from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.canonical import CanonicalCreate, CanonicalOut, LinkItemRequest
from app.api.schemas.items import ShoppingListItemOut
from app.services import canonical_service, item_service

router = APIRouter(prefix="/canonicals", tags=["canonicals"])


@router.post("", response_model=CanonicalOut, status_code=201)
def create_canonical(body: CanonicalCreate, db: Session = Depends(get_db)):
    return canonical_service.create_canonical(db, body.model_dump())


@router.get("", response_model=list[CanonicalOut])
def list_canonicals(
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None, min_length=2),
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if q:
        return canonical_service.search_canonicals(db, q)
    return canonical_service.list_canonicals(db, category, limit, offset)


@router.get("/{canonical_id}", response_model=CanonicalOut)
def get_canonical(canonical_id: str, db: Session = Depends(get_db)):
    c = canonical_service.get_canonical(db, canonical_id)
    if not c:
        raise HTTPException(status_code=404, detail="Canonical not found")
    return c


@router.post("/items/{item_id}/link", response_model=ShoppingListItemOut)
def link_item(item_id: str, body: LinkItemRequest, db: Session = Depends(get_db)):
    """Vincula un item de lista a un producto canónico para habilitar comparación de equivalentes."""
    item = canonical_service.link_item_to_canonical(db, item_id, body.canonical_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
