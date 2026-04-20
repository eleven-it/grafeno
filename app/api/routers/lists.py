from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.lists import ShoppingListCreate, ShoppingListUpdate, ShoppingListOut
from app.services import list_service

router = APIRouter(prefix="/lists", tags=["lists"])


def _get_demo_user(db: Session) -> str:
    user = list_service.get_or_create_demo_user(db)
    return user.id


@router.post("", response_model=ShoppingListOut, status_code=status.HTTP_201_CREATED)
def create_list(body: ShoppingListCreate, db: Session = Depends(get_db)):
    user_id = _get_demo_user(db)
    return list_service.create_list(db, user_id, body.model_dump())


@router.get("", response_model=list[ShoppingListOut])
def get_lists(db: Session = Depends(get_db)):
    user_id = _get_demo_user(db)
    return list_service.get_lists(db, user_id)


@router.get("/{list_id}", response_model=ShoppingListOut)
def get_list(list_id: str, db: Session = Depends(get_db)):
    lst = list_service.get_list(db, list_id)
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    return lst


@router.patch("/{list_id}", response_model=ShoppingListOut)
def update_list(list_id: str, body: ShoppingListUpdate, db: Session = Depends(get_db)):
    lst = list_service.update_list(db, list_id, body.model_dump(exclude_none=True))
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")
    return lst


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_list(list_id: str, db: Session = Depends(get_db)):
    ok = list_service.delete_list(db, list_id)
    if not ok:
        raise HTTPException(status_code=404, detail="List not found")
