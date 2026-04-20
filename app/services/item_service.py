from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models import ShoppingListItem
import uuid


def create_item(db: Session, list_id: str, data: dict) -> ShoppingListItem:
    item = ShoppingListItem(
        id=str(uuid.uuid4()),
        list_id=list_id,
        original_text=data["original_text"],
        category=data.get("category"),
        preferred_brand=data.get("preferred_brand"),
        excluded_brands=data.get("excluded_brands"),
        desired_presentation=data.get("desired_presentation"),
        desired_quantity=data.get("desired_quantity", 1),
        target_price=data.get("target_price"),
        priority=data.get("priority", "medium"),
        allowed_stores=data.get("allowed_stores"),
        excluded_stores=data.get("excluded_stores"),
        allow_equivalents=data.get("allow_equivalents", True),
        allow_bulk=data.get("allow_bulk", True),
        status="active",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_item(db: Session, item_id: str) -> Optional[ShoppingListItem]:
    return db.query(ShoppingListItem).filter_by(id=item_id).first()


def get_items_for_list(db: Session, list_id: str) -> list[ShoppingListItem]:
    return db.query(ShoppingListItem).filter_by(list_id=list_id).all()


def update_item(db: Session, item_id: str, data: dict) -> Optional[ShoppingListItem]:
    item = get_item(db, item_id)
    if not item:
        return None
    allowed = {
        "original_text", "category", "preferred_brand", "excluded_brands",
        "desired_presentation", "desired_quantity", "target_price", "priority",
        "allowed_stores", "excluded_stores", "allow_equivalents", "allow_bulk",
        "status", "canonical_product_id",
    }
    for key, val in data.items():
        if key in allowed:
            setattr(item, key, val)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, item_id: str) -> bool:
    item = get_item(db, item_id)
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True
