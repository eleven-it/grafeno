"""
Tests de integración: flujo completo list → item → offer → recommendation.
Usan SQLite en memoria (via conftest.py fixture).
"""
import pytest
from decimal import Decimal
from app.services import list_service, item_service, offer_service, recommendation


class TestFullFlow:
    def test_create_list_and_item(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {
            "name": "Test list", "list_type": "recurrent",
        })
        assert lst.id is not None
        assert lst.status == "active"

        item = item_service.create_item(db, lst.id, {
            "original_text": "leche entera 1L",
            "category": "leche",
        })
        assert item.list_id == lst.id

    def test_import_offer_calculates_unit_economics(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "Test"})
        item = item_service.create_item(db, lst.id, {"original_text": "leche"})

        offer = offer_service.import_offer(db, {
            "item_id": item.id,
            "source": "carrefour",
            "retailer": "Carrefour",
            "title": "Leche Entera La Serenísima 1 L",
            "price": 1100,
            "currency": "ARS",
            "in_stock": True,
        })

        assert offer.price_per_base_unit == Decimal("1100.0000")
        assert offer.normalized_unit == "L"
        assert offer.total_quantity == Decimal("1")

    def test_recommendation_picks_best_unit_value(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "Test"})
        item = item_service.create_item(db, lst.id, {
            "original_text": "leche", "allow_equivalents": False
        })

        for title, price in [
            ("Leche 500 ml", 700),
            ("Leche 1 L", 1100),
            ("Leche Bidón 5 L", 4800),
        ]:
            offer_service.import_offer(db, {
                "item_id": item.id,
                "source": "carrefour",
                "retailer": "Carrefour",
                "title": title,
                "price": price,
                "currency": "ARS",
                "in_stock": True,
            })

        rec = recommendation.recommend_item(db, item.id)
        assert rec is not None
        # Bidón 5L = 960/L → mejor valor unitario
        assert rec.best_unit_value is not None
        assert "5" in rec.best_unit_value.title or "960" in str(rec.best_unit_value.price_per_base_unit)
        # 500ml = $700 → menor desembolso
        assert rec.best_total_price is not None
        assert rec.best_total_price.price == Decimal("700")

    def test_delete_list(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "To delete"})
        ok = list_service.delete_list(db, lst.id)
        assert ok
        assert list_service.get_list(db, lst.id) is None

    def test_get_lists_for_user(self, db):
        user = list_service.get_or_create_demo_user(db)
        list_service.create_list(db, user.id, {"name": "Lista A"})
        list_service.create_list(db, user.id, {"name": "Lista B"})
        lists = list_service.get_lists(db, user.id)
        assert len(lists) == 2
