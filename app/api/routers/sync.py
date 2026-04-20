"""
Endpoints para sincronizar ofertas desde conectores y buscar en fuentes.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.schemas.sync import ListSyncSummaryOut, SyncResultOut, SearchResultOut
from app.services import sync_service, item_service, list_service

router = APIRouter(tags=["sync"])


@router.post("/lists/{list_id}/sync", response_model=ListSyncSummaryOut)
def sync_list(
    list_id: str,
    connectors: Optional[str] = Query(None, description="CSV de conectores, ej: mock,carrefour"),
    db: Session = Depends(get_db),
):
    """
    Sincroniza ofertas para todos los items activos de una lista.
    Busca en los conectores registrados y persiste las ofertas que hacen match.
    """
    lst = list_service.get_list(db, list_id)
    if not lst:
        raise HTTPException(status_code=404, detail="List not found")

    connector_ids = connectors.split(",") if connectors else None
    summary = sync_service.sync_list(db, list_id, connector_ids)

    return ListSyncSummaryOut(
        list_id=summary.list_id,
        items_synced=summary.items_synced,
        total_offers_imported=summary.total_offers_imported,
        results=[
            SyncResultOut(
                item_id=r.item_id,
                item_text=r.item_text,
                connector=r.connector,
                offers_found=r.offers_found,
                offers_imported=r.offers_imported,
                offers_skipped=r.offers_skipped,
            )
            for r in summary.results
        ],
    )


@router.post("/items/{item_id}/sync", response_model=list[SyncResultOut])
def sync_item(
    item_id: str,
    connectors: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Sincroniza ofertas para un item específico desde los conectores.
    """
    item = item_service.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    connector_ids = connectors.split(",") if connectors else None
    results = sync_service.sync_item(db, item, connector_ids)

    return [
        SyncResultOut(
            item_id=r.item_id,
            item_text=r.item_text,
            connector=r.connector,
            offers_found=r.offers_found,
            offers_imported=r.offers_imported,
            offers_skipped=r.offers_skipped,
        )
        for r in results
    ]


@router.get("/sources/search", response_model=list[SearchResultOut])
def search_sources(
    q: str = Query(..., min_length=2, description="Texto a buscar"),
    connector: str = Query("mock", description="ID del conector"),
    source: Optional[str] = Query(None, description="Filtrar por fuente, ej: carrefour"),
):
    """
    Busca en un conector sin persistir. Útil para explorar disponibilidad
    antes de agregar un item a una lista.
    """
    results = sync_service.search_connector(q, connector, source)
    return [
        SearchResultOut(
            source=r["source"],
            retailer=r["retailer"],
            title=r["title"],
            price=r["price"],
            currency=r["currency"],
            in_stock=r["in_stock"],
            detected_brand=r.get("detected_brand"),
            detected_category=r.get("detected_category"),
            promo_description=r.get("promo_description"),
            url=r.get("url"),
            external_sku=r.get("external_sku"),
        )
        for r in results
    ]


@router.get("/sources", response_model=list[dict])
def list_sources():
    """Lista los conectores disponibles y su estado."""
    return [
        {"id": cid, "source_type": conn.source_type, "status": "available"}
        for cid, conn in sync_service.REGISTRY.items()
    ]
