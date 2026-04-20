from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.offers import OfferImport, OfferBatchImport, OfferOut
from app.services import offer_service

router = APIRouter(prefix="/offers", tags=["offers"])


@router.post("/import", response_model=OfferOut, status_code=status.HTTP_201_CREATED)
def import_offer(body: OfferImport, db: Session = Depends(get_db)):
    return offer_service.import_offer(db, body.model_dump())


@router.post("/import/batch", response_model=list[OfferOut], status_code=status.HTTP_201_CREATED)
def import_offers_batch(body: OfferBatchImport, db: Session = Depends(get_db)):
    return offer_service.import_offers_batch(db, [o.model_dump() for o in body.offers])
