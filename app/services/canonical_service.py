"""
Gestión de productos canónicos.
Un ProductCanonical actúa como "anchor" para agrupar
ofertas equivalentes de distintas fuentes y presentaciones.
"""
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models import ProductCanonical, ShoppingListItem


def create_canonical(db: Session, data: dict) -> ProductCanonical:
    canon = ProductCanonical(
        id=str(uuid.uuid4()),
        name=data["name"],
        category=data["category"],
        base_unit=data.get("base_unit", "unit"),
        attributes=data.get("attributes", {}),
    )
    db.add(canon)
    db.commit()
    db.refresh(canon)
    return canon


def get_canonical(db: Session, canonical_id: str) -> Optional[ProductCanonical]:
    return db.query(ProductCanonical).filter_by(id=canonical_id).first()


def list_canonicals(
    db: Session,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[ProductCanonical]:
    q = db.query(ProductCanonical)
    if category:
        q = q.filter_by(category=category)
    return q.order_by(ProductCanonical.name).offset(offset).limit(limit).all()


def link_item_to_canonical(
    db: Session,
    item_id: str,
    canonical_id: str,
) -> Optional[ShoppingListItem]:
    """Asocia un item de lista con un producto canónico para habilitar equivalentes."""
    item = db.query(ShoppingListItem).filter_by(id=item_id).first()
    if not item:
        return None
    item.canonical_product_id = canonical_id
    db.commit()
    db.refresh(item)
    return item


def search_canonicals(db: Session, query: str) -> list[ProductCanonical]:
    """Búsqueda simple por nombre (ILIKE)."""
    return (
        db.query(ProductCanonical)
        .filter(ProductCanonical.name.ilike(f"%{query}%"))
        .limit(20)
        .all()
    )
