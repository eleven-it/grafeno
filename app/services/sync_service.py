"""
Servicio de sincronización de ofertas desde conectores externos.

Flujo:
  1. Para cada item activo de una lista (o un item específico),
     busca en los conectores registrados usando el texto del item.
  2. Calcula matching score contra el item.
  3. Importa las ofertas que superan el umbral de confianza.

Los conectores son pluggeables: agregar uno nuevo = instanciarlo en REGISTRY.
"""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session

from app.connectors.base import BaseConnector, RawOffer
from app.connectors.mock import MockConnector
from app.domain.models import ShoppingListItem, ShoppingList
from app.services import offer_service
from app.services.matching import match_score


# ---------------------------------------------------------------------------
# Registro de conectores disponibles
# ---------------------------------------------------------------------------

REGISTRY: dict[str, BaseConnector] = {
    "mock": MockConnector(),
    # "carrefour": CarrefourConnector(),   # agregar cuando exista
    # "mercadolibre": MercadoLibreConnector(),
}


@dataclass
class SyncResult:
    item_id: str
    item_text: str
    connector: str
    offers_found: int
    offers_imported: int
    offers_skipped: int


@dataclass
class ListSyncSummary:
    list_id: str
    items_synced: int
    total_offers_imported: int
    results: list[SyncResult]


def sync_item(
    db: Session,
    item: ShoppingListItem,
    connector_ids: Optional[list[str]] = None,
    match_threshold: float = 0.35,
) -> list[SyncResult]:
    """
    Sincroniza ofertas para un item desde los conectores indicados.
    Si connector_ids es None, usa todos los registrados.
    """
    connectors = _resolve_connectors(connector_ids)
    results: list[SyncResult] = []

    for conn_id, connector in connectors.items():
        raw_offers = connector.search(item.original_text)
        imported = 0
        skipped = 0

        for raw in raw_offers:
            # Filtrar tiendas excluidas
            if item.excluded_stores and raw.source in item.excluded_stores:
                skipped += 1
                continue
            if item.allowed_stores and raw.source not in item.allowed_stores:
                skipped += 1
                continue

            # Filtrar marcas excluidas
            if (
                item.excluded_brands
                and raw.detected_brand
                and raw.detected_brand.lower() in [b.lower() for b in item.excluded_brands]
            ):
                skipped += 1
                continue

            # Matching score
            score = match_score(item.original_text, raw.title)
            if score.score < match_threshold:
                skipped += 1
                continue

            offer_dict = raw.to_dict()
            offer_dict["item_id"] = item.id
            offer_dict["matching_score"] = score.score
            offer_dict["confidence_score"] = score.confidence

            offer_service.import_offer(db, offer_dict)
            imported += 1

        results.append(SyncResult(
            item_id=item.id,
            item_text=item.original_text,
            connector=conn_id,
            offers_found=len(raw_offers),
            offers_imported=imported,
            offers_skipped=skipped,
        ))

    return results


def sync_list(
    db: Session,
    list_id: str,
    connector_ids: Optional[list[str]] = None,
) -> Optional[ListSyncSummary]:
    """
    Sincroniza todos los items activos de una lista.
    """
    lst: Optional[ShoppingList] = db.query(ShoppingList).filter_by(id=list_id).first()
    if not lst:
        return None

    active_items = [i for i in lst.items if i.status == "active"]
    all_results: list[SyncResult] = []
    total_imported = 0

    for item in active_items:
        item_results = sync_item(db, item, connector_ids)
        all_results.extend(item_results)
        total_imported += sum(r.offers_imported for r in item_results)

    return ListSyncSummary(
        list_id=list_id,
        items_synced=len(active_items),
        total_offers_imported=total_imported,
        results=all_results,
    )


def search_connector(
    query: str,
    connector_id: str = "mock",
    source_filter: Optional[str] = None,
) -> list[dict]:
    """
    Busca en un conector específico sin persistir. Útil para exploración.
    """
    connector = REGISTRY.get(connector_id)
    if not connector:
        return []

    kwargs = {}
    if source_filter:
        kwargs["source"] = source_filter

    raw_offers = connector.search(query, **kwargs)
    return [o.to_dict() for o in raw_offers]


def _resolve_connectors(connector_ids: Optional[list[str]]) -> dict[str, BaseConnector]:
    if not connector_ids:
        return REGISTRY
    return {k: v for k, v in REGISTRY.items() if k in connector_ids}
