"""
Tests del servicio de historial de precios.
"""
import pytest
from decimal import Decimal
from app.services import list_service, item_service, offer_service, price_history as ph


class TestPriceHistory:
    def _make_item_with_offers(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "Test"})
        item = item_service.create_item(db, lst.id, {"original_text": "leche 1L"})

        for source, price in [
            ("carrefour", 1100),
            ("carrefour", 1050),   # baja de precio
            ("walmart", 980),
            ("walmart", 990),
        ]:
            offer_service.import_offer(db, {
                "item_id": item.id,
                "source": source,
                "retailer": source.capitalize(),
                "title": "Leche Entera 1 L",
                "price": price,
                "currency": "ARS",
                "in_stock": True,
            })
        return item

    def test_returns_history(self, db):
        item = self._make_item_with_offers(db)
        history = ph.get_price_history(db, item.id)
        assert history is not None
        assert len(history.series) == 2   # carrefour y walmart

    def test_series_per_source(self, db):
        item = self._make_item_with_offers(db)
        history = ph.get_price_history(db, item.id)
        sources = {s.source for s in history.series}
        assert "carrefour" in sources
        assert "walmart" in sources

    def test_min_max_correct(self, db):
        item = self._make_item_with_offers(db)
        history = ph.get_price_history(db, item.id)
        assert history.overall_min == Decimal("980")
        assert history.overall_max == Decimal("1100")

    def test_best_current_source(self, db):
        item = self._make_item_with_offers(db)
        history = ph.get_price_history(db, item.id)
        # walmart tiene el precio más bajo (980 y 990)
        assert history.best_current_source == "walmart"

    def test_no_history_returns_none(self, db):
        user = list_service.get_or_create_demo_user(db)
        lst = list_service.create_list(db, user.id, {"name": "Test"})
        item = item_service.create_item(db, lst.id, {"original_text": "sin ofertas"})
        history = ph.get_price_history(db, item.id)
        assert history is None

    def test_price_change_pct_calculated(self, db):
        item = self._make_item_with_offers(db)
        history = ph.get_price_history(db, item.id)
        carrefour_series = next(s for s in history.series if s.source == "carrefour")
        # carrefour: 1100 → 1050 = -4.5%
        assert carrefour_series.price_change_pct is not None
        assert carrefour_series.price_change_pct < 0   # bajó
