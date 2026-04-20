"""
Conector mock con datos de demo realistas.
Simula múltiples fuentes: Carrefour, Walmart, Easy, MercadoLibre.
Usado para pruebas y demos sin depender de scraping real.
"""
from decimal import Decimal
from typing import Optional
from app.connectors.base import BaseConnector, RawOffer


# ---------------------------------------------------------------------------
# Catálogo de ofertas demo
# ---------------------------------------------------------------------------

MOCK_CATALOG: list[dict] = [
    # --- LECHE ---
    {
        "source": "carrefour", "retailer": "Carrefour", "source_type": "supermarket",
        "title": "Leche Entera La Serenísima 500 ml",
        "price": 700, "currency": "ARS", "in_stock": True,
        "detected_brand": "La Serenísima", "detected_category": "leche",
        "url": "https://mock.carrefour.com/leche-serenisima-500ml",
        "external_sku": "CAR-LAC-001",
    },
    {
        "source": "carrefour", "retailer": "Carrefour", "source_type": "supermarket",
        "title": "Leche Entera La Serenísima 1 L",
        "price": 1100, "currency": "ARS", "in_stock": True,
        "detected_brand": "La Serenísima", "detected_category": "leche",
        "url": "https://mock.carrefour.com/leche-serenisima-1l",
        "external_sku": "CAR-LAC-002",
    },
    {
        "source": "carrefour", "retailer": "Carrefour", "source_type": "supermarket",
        "title": "Leche Entera La Serenísima Bidón 5 L",
        "price": 4800, "currency": "ARS", "in_stock": True,
        "detected_brand": "La Serenísima", "detected_category": "leche",
        "url": "https://mock.carrefour.com/leche-serenisima-5l",
        "external_sku": "CAR-LAC-003",
    },
    {
        "source": "walmart", "retailer": "Walmart", "source_type": "supermarket",
        "title": "Leche Entera La Serenísima Pack 6 x 1L",
        "price": 5900, "currency": "ARS", "in_stock": True,
        "detected_brand": "La Serenísima", "detected_category": "leche",
        "promo_description": "Precio especial pack",
        "url": "https://mock.walmart.com/leche-serenisima-6x1l",
        "external_sku": "WAL-LAC-006",
    },
    {
        "source": "walmart", "retailer": "Walmart", "source_type": "supermarket",
        "title": "Leche Entera Sancor 1 L",
        "price": 980, "currency": "ARS", "in_stock": True,
        "detected_brand": "Sancor", "detected_category": "leche",
        "url": "https://mock.walmart.com/leche-sancor-1l",
        "external_sku": "WAL-LAC-010",
    },
    # --- DETERGENTE ---
    {
        "source": "carrefour", "retailer": "Carrefour", "source_type": "supermarket",
        "title": "Detergente Magistral 500 ml",
        "price": 850, "currency": "ARS", "in_stock": True,
        "detected_brand": "Magistral", "detected_category": "detergente",
        "external_sku": "CAR-DET-001",
    },
    {
        "source": "carrefour", "retailer": "Carrefour", "source_type": "supermarket",
        "title": "Detergente Magistral 750 ml",
        "price": 1150, "currency": "ARS", "in_stock": True,
        "detected_brand": "Magistral", "detected_category": "detergente",
        "promo_description": "10% off",
        "original_price": 1280,
        "external_sku": "CAR-DET-002",
    },
    {
        "source": "walmart", "retailer": "Walmart", "source_type": "supermarket",
        "title": "Detergente Magistral Pack 3 x 750 ml",
        "price": 2900, "currency": "ARS", "in_stock": True,
        "detected_brand": "Magistral", "detected_category": "detergente",
        "promo_description": "Pack familiar",
        "external_sku": "WAL-DET-003",
    },
    # --- ARROZ ---
    {
        "source": "coto", "retailer": "Coto", "source_type": "supermarket",
        "title": "Arroz Largo Fino Gallo 500 g",
        "price": 620, "currency": "ARS", "in_stock": True,
        "detected_brand": "Gallo", "detected_category": "arroz",
        "external_sku": "COT-ARR-001",
    },
    {
        "source": "coto", "retailer": "Coto", "source_type": "supermarket",
        "title": "Arroz Largo Fino Gallo 1 kg",
        "price": 980, "currency": "ARS", "in_stock": True,
        "detected_brand": "Gallo", "detected_category": "arroz",
        "external_sku": "COT-ARR-002",
    },
    {
        "source": "coto", "retailer": "Coto", "source_type": "supermarket",
        "title": "Arroz Largo Fino Gallo 5 kg",
        "price": 3900, "currency": "ARS", "in_stock": True,
        "detected_brand": "Gallo", "detected_category": "arroz",
        "external_sku": "COT-ARR-003",
    },
    # --- PINTURA (retail hogar/construcción) ---
    {
        "source": "easy", "retailer": "Easy", "source_type": "retail",
        "title": "Látex Interior Sherwin Williams 1 L",
        "price": 4500, "currency": "ARS", "in_stock": True,
        "detected_brand": "Sherwin Williams", "detected_category": "pintura",
        "external_sku": "EAS-PIN-001",
    },
    {
        "source": "easy", "retailer": "Easy", "source_type": "retail",
        "title": "Látex Interior Sherwin Williams 4 L",
        "price": 14800, "currency": "ARS", "in_stock": True,
        "detected_brand": "Sherwin Williams", "detected_category": "pintura",
        "external_sku": "EAS-PIN-002",
    },
    {
        "source": "sodimac", "retailer": "Sodimac", "source_type": "retail",
        "title": "Látex Interior Sherwin Williams 20 L",
        "price": 58000, "currency": "ARS", "in_stock": False,
        "detected_brand": "Sherwin Williams", "detected_category": "pintura",
        "external_sku": "SOD-PIN-003",
    },
    # --- MARKETPLACE ---
    {
        "source": "mercadolibre", "retailer": "MercadoLibre", "source_type": "marketplace",
        "title": "Leche Larga Vida Entera La Serenísima 1000cc x 12 unidades",
        "price": 11500, "currency": "ARS", "in_stock": True,
        "detected_brand": "La Serenísima", "detected_category": "leche",
        "promo_description": "12% off",
        "original_price": 13068,
        "seller": "super_ahorro_oficial",
        "installments": {"count": 3, "amount": 3834, "interest": False},
        "external_sku": "MLA-1234567",
        "url": "https://mock.mercadolibre.com/MLA-1234567",
    },
]


class MockConnector(BaseConnector):
    """
    Conector mock. Devuelve datos del catálogo estático filtrados por query.
    Simula Carrefour, Walmart, Coto, Easy, Sodimac y MercadoLibre.
    """

    @property
    def source_id(self) -> str:
        return "mock_all"

    @property
    def source_type(self) -> str:
        return "mixed"

    def search(self, query: str, source: Optional[str] = None, **kwargs) -> list[RawOffer]:
        query_lower = query.lower()
        results = []
        for item in MOCK_CATALOG:
            if source and item["source"] != source:
                continue
            if query_lower in item["title"].lower() or query_lower in item.get("detected_category", ""):
                results.append(self._to_raw_offer(item))
        return results

    def get_offer(self, external_sku: str) -> Optional[RawOffer]:
        for item in MOCK_CATALOG:
            if item.get("external_sku") == external_sku:
                return self._to_raw_offer(item)
        return None

    def get_all(self, source: Optional[str] = None) -> list[RawOffer]:
        items = MOCK_CATALOG if not source else [i for i in MOCK_CATALOG if i["source"] == source]
        return [self._to_raw_offer(i) for i in items]

    @staticmethod
    def _to_raw_offer(item: dict) -> RawOffer:
        return RawOffer(
            source=item["source"],
            retailer=item["retailer"],
            source_type=item["source_type"],
            title=item["title"],
            price=Decimal(str(item["price"])),
            currency=item.get("currency", "ARS"),
            in_stock=item.get("in_stock", True),
            url=item.get("url"),
            external_sku=item.get("external_sku"),
            detected_brand=item.get("detected_brand"),
            detected_category=item.get("detected_category"),
            original_price=Decimal(str(item["original_price"])) if item.get("original_price") else None,
            shipping_cost=Decimal(str(item["shipping_cost"])) if item.get("shipping_cost") else None,
            promo_description=item.get("promo_description"),
            installments=item.get("installments"),
            seller=item.get("seller"),
            image_url=item.get("image_url"),
            raw_attributes={k: v for k, v in item.items() if k not in {
                "source", "retailer", "source_type", "title", "price", "currency",
                "in_stock", "url", "external_sku", "detected_brand", "detected_category",
                "original_price", "shipping_cost", "promo_description", "installments",
                "seller", "image_url",
            }},
        )
