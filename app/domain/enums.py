from enum import Enum


class ListType(str, Enum):
    RECURRENT = "recurrent"
    PROJECT = "project"
    WISHLIST = "wishlist"
    EVENT = "event"


class ListStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


class MonitoringFrequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"


class ItemPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ItemStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    PURCHASED = "purchased"


class AlertRuleType(str, Enum):
    PRICE_BELOW = "price_below"           # precio absoluto por debajo del umbral
    PRICE_DROP_PCT = "price_drop_pct"     # baja porcentual desde último precio
    BACK_IN_STOCK = "back_in_stock"       # vuelve a haber stock
    BETTER_EQUIVALENT = "better_equivalent"  # aparece equivalente más barato
    UNIT_PRICE_BELOW = "unit_price_below" # precio por unidad base por debajo


class BaseUnit(str, Enum):
    """Unidades base comparables para unit economics."""
    LITER = "L"
    KG = "kg"
    UNIT = "unit"
    METER = "m"
    M2 = "m2"
    M3 = "m3"


class SourceType(str, Enum):
    SUPERMARKET = "supermarket"
    RETAIL = "retail"
    MARKETPLACE = "marketplace"
