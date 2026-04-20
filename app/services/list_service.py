from typing import Optional
from sqlalchemy.orm import Session
from app.domain.models import ShoppingList, User
import uuid


def get_or_create_demo_user(db: Session) -> User:
    """Para MVP: usuario de demo fijo."""
    user = db.query(User).filter_by(email="demo@grafeno.app").first()
    if not user:
        user = User(id=str(uuid.uuid4()), email="demo@grafeno.app", name="Demo User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def create_list(db: Session, user_id: str, data: dict) -> ShoppingList:
    shopping_list = ShoppingList(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=data["name"],
        description=data.get("description"),
        list_type=data.get("list_type", "recurrent"),
        country=data.get("country", "AR"),
        currency=data.get("currency", "ARS"),
        budget=data.get("budget"),
        monitoring_frequency=data.get("monitoring_frequency", "daily"),
        status="active",
    )
    db.add(shopping_list)
    db.commit()
    db.refresh(shopping_list)
    return shopping_list


def get_list(db: Session, list_id: str) -> Optional[ShoppingList]:
    return db.query(ShoppingList).filter_by(id=list_id).first()


def get_lists(db: Session, user_id: str) -> list[ShoppingList]:
    return db.query(ShoppingList).filter_by(user_id=user_id).all()


def update_list(db: Session, list_id: str, data: dict) -> Optional[ShoppingList]:
    lst = get_list(db, list_id)
    if not lst:
        return None
    allowed = {"name", "description", "list_type", "country", "currency",
               "budget", "monitoring_frequency", "status"}
    for key, val in data.items():
        if key in allowed:
            setattr(lst, key, val)
    db.commit()
    db.refresh(lst)
    return lst


def delete_list(db: Session, list_id: str) -> bool:
    lst = get_list(db, list_id)
    if not lst:
        return False
    db.delete(lst)
    db.commit()
    return True
