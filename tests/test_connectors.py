"""
Tests del mock connector y su integración con el servicio de ofertas.
"""
import pytest
from app.connectors.mock import MockConnector


class TestMockConnector:
    def setup_method(self):
        self.connector = MockConnector()

    def test_search_leche_returns_results(self):
        results = self.connector.search("leche")
        assert len(results) >= 3  # al menos 500ml, 1L, 5L

    def test_search_by_source(self):
        results = self.connector.search("leche", source="carrefour")
        assert all(r.source == "carrefour" for r in results)

    def test_get_offer_by_sku(self):
        offer = self.connector.get_offer("CAR-LAC-001")
        assert offer is not None
        assert "500" in offer.title or "500" in offer.title

    def test_get_all_returns_multiple_sources(self):
        all_offers = self.connector.get_all()
        sources = {o.source for o in all_offers}
        assert len(sources) >= 3

    def test_raw_offer_to_dict(self):
        results = self.connector.search("arroz")
        assert len(results) > 0
        d = results[0].to_dict()
        assert "title" in d
        assert "price" in d
        assert "source" in d

    def test_marketplace_offer_has_installments(self):
        offer = self.connector.get_offer("MLA-1234567")
        assert offer is not None
        assert offer.installments is not None
        assert offer.seller is not None

    def test_out_of_stock_offer_exists(self):
        all_offers = self.connector.get_all()
        oos = [o for o in all_offers if not o.in_stock]
        assert len(oos) >= 1
