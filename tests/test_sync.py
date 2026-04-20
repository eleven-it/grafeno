"""
Tests de sync service e integración con connectors.
"""
import pytest
from app.services import list_service, item_service, sync_service


class TestSyncService:
    def test_sync_item_imports_offers(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "Test"})
        item = item_service.create_item(db, lst.id, {
            "original_text": "leche entera",
            "category": "leche",
        })

        results = sync_service.sync_item(db, item)
        assert len(results) > 0
        total_imported = sum(r.offers_imported for r in results)
        assert total_imported > 0

    def test_sync_item_filters_excluded_stores(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "Test"})
        item = item_service.create_item(db, lst.id, {
            "original_text": "leche entera",
            "excluded_stores": ["carrefour", "walmart", "coto", "mercadolibre"],
        })

        results = sync_service.sync_item(db, item)
        total_imported = sum(r.offers_imported for r in results)
        assert total_imported == 0   # todo excluido

    def test_sync_list_processes_all_active_items(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "Test"})
        item_service.create_item(db, lst.id, {"original_text": "leche"})
        item_service.create_item(db, lst.id, {"original_text": "arroz"})
        # item pausado no debe sincronizarse
        paused = item_service.create_item(db, lst.id, {"original_text": "detergente"})
        item_service.update_item(db, paused.id, {"status": "paused"})

        summary = sync_service.sync_list(db, lst.id)
        assert summary is not None
        assert summary.items_synced == 2

    def test_sync_list_not_found_returns_none(self, db):
        summary = sync_service.sync_list(db, "nonexistent-id")
        assert summary is None

    def test_search_connector_returns_results(self):
        results = sync_service.search_connector("leche", "mock")
        assert len(results) > 0
        assert all("title" in r for r in results)

    def test_search_connector_unknown_returns_empty(self):
        results = sync_service.search_connector("leche", "nonexistent")
        assert results == []

    def test_sync_respects_match_threshold(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "Test"})
        # Texto muy diferente a cualquier oferta del mock
        item = item_service.create_item(db, lst.id, {
            "original_text": "zzz producto inexistente xyz"
        })

        results = sync_service.sync_item(db, item, match_threshold=0.80)
        total_imported = sum(r.offers_imported for r in results)
        assert total_imported == 0
