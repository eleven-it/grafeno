"""
Interfaz base para conectores de fuentes de precios.
Cada retailer o marketplace implementa esta interfaz.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class RawOffer:
    """Oferta cruda tal como viene de la fuente."""
    source: str
    retailer: str
    source_type: str                 # supermarket | retail | marketplace
    title: str
    price: Decimal
    currency: str
    in_stock: bool
    url: Optional[str] = None
    external_sku: Optional[str] = None
    detected_brand: Optional[str] = None
    detected_category: Optional[str] = None
    original_price: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None
    promo_description: Optional[str] = None
    installments: Optional[dict] = None
    seller: Optional[str] = None
    image_url: Optional[str] = None
    raw_attributes: dict = None

    def __post_init__(self):
        if self.raw_attributes is None:
            self.raw_attributes = {}

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "retailer": self.retailer,
            "source_type": self.source_type,
            "title": self.title,
            "price": float(self.price),
            "currency": self.currency,
            "in_stock": self.in_stock,
            "url": self.url,
            "external_sku": self.external_sku,
            "detected_brand": self.detected_brand,
            "detected_category": self.detected_category,
            "original_price": float(self.original_price) if self.original_price else None,
            "shipping_cost": float(self.shipping_cost) if self.shipping_cost else None,
            "promo_description": self.promo_description,
            "installments": self.installments,
            "seller": self.seller,
            "image_url": self.image_url,
            "raw_attributes": self.raw_attributes,
        }


class BaseConnector(ABC):
    """
    Interfaz que deben implementar todos los conectores de fuentes.
    Un conector puede ser un scraper, un adaptador de API, o un mock.
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Identificador único de la fuente, ej: 'carrefour_ar'."""
        ...

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Tipo: supermarket | retail | marketplace."""
        ...

    @abstractmethod
    def search(self, query: str, **kwargs) -> list[RawOffer]:
        """
        Busca ofertas para un query dado.
        Implementaciones reales harán scraping o llamadas API.
        """
        ...

    @abstractmethod
    def get_offer(self, external_sku: str) -> Optional[RawOffer]:
        """Obtiene una oferta específica por SKU externo."""
        ...
