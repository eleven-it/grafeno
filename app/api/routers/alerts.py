from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from app.api.deps import get_db
from app.api.schemas.alerts import AlertRuleCreate, AlertRuleOut, AlertEventOut
from app.services import alert_service, list_service, item_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/rules", response_model=AlertRuleOut, status_code=201)
def create_rule(body: AlertRuleCreate, db: Session = Depends(get_db)):
    return alert_service.create_rule(db, body.item_id, body.model_dump(exclude={"item_id"}))


@router.get("/rules", response_model=list[AlertRuleOut])
def get_rules(item_id: Optional[str] = None, db: Session = Depends(get_db)):
    return alert_service.get_rules(db, item_id)


@router.get("/events", response_model=list[AlertEventOut])
def get_events(item_id: Optional[str] = None, db: Session = Depends(get_db)):
    return alert_service.get_events(db, item_id)


@router.post("/evaluate/{item_id}", response_model=list[AlertEventOut])
def evaluate_alerts(item_id: str, db: Session = Depends(get_db)):
    """Evalúa alertas manualmente para un item. En producción esto corre en un worker."""
    return alert_service.evaluate_rules_for_item(db, item_id)


@router.post("/evaluate-list/{list_id}", response_model=list[AlertEventOut])
def evaluate_list_alerts(list_id: str, db: Session = Depends(get_db)):
    """Evalúa todas las alertas de todos los items activos de una lista."""
    lst = list_service.get_list(db, list_id)
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    all_events: list = []
    for item in lst.items:
        if item.status == "active":
            events = alert_service.evaluate_rules_for_item(db, item.id)
            all_events.extend(events)
    return all_events
