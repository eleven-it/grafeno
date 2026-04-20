"""
Motor de unit economics. Convierte precios a una unidad base común
y calcula precio por unidad comparable para cualquier presentación.

Unidades base soportadas:
  - Volumen:  L  (litros)
  - Peso:     kg
  - Largo:    m
  - Área:     m2
  - Volumen:  m3
  - Count:    unit

Todas las conversiones son determinísticas y sin lógica de LLM.
"""
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional
import re


# ---------------------------------------------------------------------------
# Factores de conversión → unidad base
# ---------------------------------------------------------------------------

VOLUME_TO_LITERS: dict[str, Decimal] = {
    "l": Decimal("1"),
    "lt": Decimal("1"),
    "lts": Decimal("1"),
    "litro": Decimal("1"),
    "litros": Decimal("1"),
    "liter": Decimal("1"),
    "liters": Decimal("1"),
    "ml": Decimal("0.001"),
    "cc": Decimal("0.001"),
    "cl": Decimal("0.01"),
    "dl": Decimal("0.1"),
}

WEIGHT_TO_KG: dict[str, Decimal] = {
    "kg": Decimal("1"),
    "kgs": Decimal("1"),
    "kilo": Decimal("1"),
    "kilos": Decimal("1"),
    "kilogram": Decimal("1"),
    "g": Decimal("0.001"),
    "gr": Decimal("0.001"),
    "grs": Decimal("0.001"),
    "gramo": Decimal("0.001"),
    "gramos": Decimal("0.001"),
    "gram": Decimal("0.001"),
    "mg": Decimal("0.000001"),
    "t": Decimal("1000"),
    "tn": Decimal("1000"),
}

LENGTH_TO_M: dict[str, Decimal] = {
    "m": Decimal("1"),
    "metro": Decimal("1"),
    "metros": Decimal("1"),
    "cm": Decimal("0.01"),
    "mm": Decimal("0.001"),
}

AREA_TO_M2: dict[str, Decimal] = {
    "m2": Decimal("1"),
    "m²": Decimal("1"),
    "cm2": Decimal("0.0001"),
    "cm²": Decimal("0.0001"),
}

VOLUME_SOLID_TO_M3: dict[str, Decimal] = {
    "m3": Decimal("1"),
    "m³": Decimal("1"),
    "l": Decimal("0.001"),   # litros también como m3 (contexto construcción)
    "cm3": Decimal("0.000001"),
    "cm³": Decimal("0.000001"),
}

COUNT_UNITS: set[str] = {"unidad", "unidades", "unit", "units", "u", "und", "pza", "pieza", "piezas"}

# Orden de preferencia de categoría de unidad
UNIT_CATEGORIES = {
    "volume": (VOLUME_TO_LITERS, "L"),
    "weight": (WEIGHT_TO_KG, "kg"),
    "length": (LENGTH_TO_M, "m"),
    "area": (AREA_TO_M2, "m2"),
    "volume_solid": (VOLUME_SOLID_TO_M3, "m3"),
    "count": (None, "unit"),
}


@dataclass
class ParsedPresentation:
    """Resultado del parsing de una presentación de producto."""
    quantity: Decimal          # cantidad numérica por envase
    raw_unit: str              # unidad tal como viene (ml, L, kg...)
    pack_size: int             # cuántos envases por pack (default 1)
    total_quantity: Decimal    # quantity * pack_size
    base_unit: str             # unidad base (L, kg, unit, m, m2, m3)
    total_in_base: Decimal     # total_quantity convertido a base_unit


@dataclass
class UnitEconomics:
    """Resultado completo de unit economics para una oferta."""
    price: Decimal
    currency: str
    presentation: ParsedPresentation
    price_per_base_unit: Decimal   # precio / total_in_base
    base_unit: str
    # Si hay precio original (promo), también calculamos sobre precio real
    effective_price: Decimal       # precio efectivo (ya con descuento si aplica)
    effective_price_per_base_unit: Decimal


# ---------------------------------------------------------------------------
# Parsing de presentaciones
# ---------------------------------------------------------------------------

# Detecta: "500 ml", "1.5 L", "5kg", "pack 6 x 1L", "6 x 500ml", etc.
_QTY_UNIT_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"        # número (con coma o punto decimal)
    r"(ml|cc|cl|dl|l|lt|lts|litro|litros|liter|liters"
    r"|mg|g|gr|grs|gramo|gramos|gram|kg|kgs|kilo|kilos|kilogram|t|tn"
    r"|mm|cm|m2|m²|cm2|cm²|m3|m³|cm3|cm³|m"
    r"|unidad|unidades|unit|units|u|und|pza|pieza|piezas)\b",
    re.IGNORECASE,
)

# Detecta: "pack de 6", "x6", "6 x", "pack x6"
_PACK_RE = re.compile(
    r"(?:pack\s*(?:de|x)?\s*|x\s*)(\d+)"
    r"|(\d+)\s*(?:x\s+(?:\d)|un(?:idades)?)",
    re.IGNORECASE,
)

# Detecta multipacks tipo "6 x 500 ml" → pack=6, qty=500, unit=ml
_MULTIPACK_RE = re.compile(
    r"(\d+)\s*[xX×]\s*(\d+(?:[.,]\d+)?)\s*"
    r"(ml|cc|cl|dl|l|lt|lts|litro|litros|liter|liters"
    r"|mg|g|gr|grs|gramo|gramos|gram|kg|kgs|kilo|kilos|kilogram"
    r"|mm|cm|m2|m²|cm2|cm²|m3|m³|m)\b",
    re.IGNORECASE,
)


def _normalize_number(s: str) -> Decimal:
    return Decimal(s.replace(",", "."))


def detect_unit_category(unit: str) -> tuple[str, Decimal, str]:
    """
    Devuelve (category, factor_to_base, base_unit).
    Raises ValueError si la unidad no es reconocida.
    """
    u = unit.lower().strip()
    if u in VOLUME_TO_LITERS:
        return "volume", VOLUME_TO_LITERS[u], "L"
    if u in WEIGHT_TO_KG:
        return "weight", WEIGHT_TO_KG[u], "kg"
    if u in AREA_TO_M2:
        return "area", AREA_TO_M2[u], "m2"
    if u in VOLUME_SOLID_TO_M3:
        # m3 puede solaparse con litros; se detecta antes area
        if u in ("m3", "m³", "cm3", "cm³"):
            return "volume_solid", VOLUME_SOLID_TO_M3[u], "m3"
    if u in LENGTH_TO_M:
        return "length", LENGTH_TO_M[u], "m"
    if u in COUNT_UNITS:
        return "count", Decimal("1"), "unit"
    raise ValueError(f"Unidad no reconocida: {unit!r}")


def parse_presentation(text: str) -> Optional[ParsedPresentation]:
    """
    Parsea el título de un producto y extrae presentación normalizada.
    Returns None si no puede determinar la presentación.

    Ejemplos:
      "Leche entera 1 L" → qty=1, unit=L, pack=1, total=1L, base=L, total_base=1L
      "Leche 500ml" → qty=0.5L base
      "Pack 6 x 1L" → qty=1, unit=L, pack=6, total=6L
      "Arroz 5kg" → qty=5, unit=kg, base=kg
    """
    text_clean = text.strip()

    # 1. Intentar multipack "6 x 500 ml"
    mp = _MULTIPACK_RE.search(text_clean)
    if mp:
        pack_size = int(mp.group(1))
        qty = _normalize_number(mp.group(2))
        unit = mp.group(3).lower()
        try:
            _, factor, base_unit = detect_unit_category(unit)
            total_qty = qty * pack_size
            total_base = total_qty * factor
            return ParsedPresentation(
                quantity=qty,
                raw_unit=unit,
                pack_size=pack_size,
                total_quantity=total_qty,
                base_unit=base_unit,
                total_in_base=total_base,
            )
        except ValueError:
            pass

    # 2. Parseo simple qty + unit
    match = _QTY_UNIT_RE.search(text_clean)
    if not match:
        return None

    qty = _normalize_number(match.group(1))
    unit = match.group(2).lower()

    try:
        _, factor, base_unit = detect_unit_category(unit)
    except ValueError:
        return None

    # 3. Detectar pack adicional en el texto
    pack_size = 1
    pack_match = _PACK_RE.search(text_clean)
    if pack_match:
        pack_val = pack_match.group(1) or pack_match.group(2)
        if pack_val:
            pack_size = int(pack_val)

    total_qty = qty * pack_size
    total_base = total_qty * factor

    return ParsedPresentation(
        quantity=qty,
        raw_unit=unit,
        pack_size=pack_size,
        total_quantity=total_qty,
        base_unit=base_unit,
        total_in_base=total_base,
    )


# ---------------------------------------------------------------------------
# Cálculo de unit economics
# ---------------------------------------------------------------------------

def calculate_unit_economics(
    price: Decimal,
    title: str,
    currency: str = "ARS",
    original_price: Optional[Decimal] = None,
    promo_description: Optional[str] = None,
) -> Optional[UnitEconomics]:
    """
    Calcula precio por unidad base para una oferta dada.
    Retorna None si no puede parsear la presentación del título.
    """
    presentation = parse_presentation(title)
    if presentation is None or presentation.total_in_base == 0:
        return None

    price_per_base = price / presentation.total_in_base

    # Precio efectivo: si hay promo 2x1, etc., intentamos aplicar
    effective_price = _apply_promo(price, promo_description)
    effective_ppu = effective_price / presentation.total_in_base

    return UnitEconomics(
        price=price,
        currency=currency,
        presentation=presentation,
        price_per_base_unit=price_per_base.quantize(Decimal("0.0001")),
        base_unit=presentation.base_unit,
        effective_price=effective_price,
        effective_price_per_base_unit=effective_ppu.quantize(Decimal("0.0001")),
    )


def _apply_promo(price: Decimal, promo: Optional[str]) -> Decimal:
    """
    Ajusta precio efectivo según promos conocidas.
    Actualmente: 2x1, 3x2, descuentos % explícitos en texto.
    """
    if not promo:
        return price

    promo_lower = promo.lower()

    # 2x1: pagás 1, llevás 2 → precio efectivo = precio / 2
    if "2x1" in promo_lower or "2 x 1" in promo_lower:
        return (price / 2).quantize(Decimal("0.01"))

    # 3x2: pagás 2, llevás 3
    if "3x2" in promo_lower or "3 x 2" in promo_lower:
        return (price * 2 / 3).quantize(Decimal("0.01"))

    # "X% off" / "X% descuento"
    pct_match = re.search(r"(\d+)\s*%", promo_lower)
    if pct_match:
        pct = Decimal(pct_match.group(1))
        return (price * (1 - pct / 100)).quantize(Decimal("0.01"))

    return price


# ---------------------------------------------------------------------------
# Comparación de presentaciones
# ---------------------------------------------------------------------------

@dataclass
class PresentationComparison:
    offer_id: str
    title: str
    source: str
    price: Decimal
    currency: str
    base_unit: str
    total_in_base: Decimal
    price_per_base_unit: Decimal
    effective_price_per_base_unit: Decimal
    in_stock: bool


@dataclass
class ComparisonResult:
    base_unit: str
    presentations: list[PresentationComparison]
    best_unit_value: Optional[PresentationComparison]       # menor precio/unidad
    best_total_price: Optional[PresentationComparison]      # menor precio absoluto
    best_practical_choice: Optional[PresentationComparison] # equilibrio razonable
    savings_vs_worst: Optional[Decimal]                     # % ahorro vs peor opción


def compare_presentations(offers: list[dict]) -> Optional[ComparisonResult]:
    """
    Compara múltiples ofertas del mismo producto base.

    Cada oferta es un dict con:
      offer_id, title, source, price, currency, original_price?,
      promo_description?, in_stock

    Retorna None si hay menos de 2 ofertas comparables.
    """
    parsed: list[PresentationComparison] = []

    for o in offers:
        ue = calculate_unit_economics(
            price=Decimal(str(o["price"])),
            title=o["title"],
            currency=o.get("currency", "ARS"),
            original_price=Decimal(str(o["original_price"])) if o.get("original_price") else None,
            promo_description=o.get("promo_description"),
        )
        if ue is None:
            continue
        parsed.append(PresentationComparison(
            offer_id=o["offer_id"],
            title=o["title"],
            source=o.get("source", ""),
            price=ue.price,
            currency=ue.currency,
            base_unit=ue.base_unit,
            total_in_base=ue.presentation.total_in_base,
            price_per_base_unit=ue.price_per_base_unit,
            effective_price_per_base_unit=ue.effective_price_per_base_unit,
            in_stock=o.get("in_stock", True),
        ))

    if len(parsed) < 1:
        return None

    # Filtrar fuera de stock para best picks (pero incluir en lista)
    in_stock = [p for p in parsed if p.in_stock]
    candidates = in_stock if in_stock else parsed

    # Agrupar por base_unit; usamos el más frecuente
    unit_counts: dict[str, int] = {}
    for p in parsed:
        unit_counts[p.base_unit] = unit_counts.get(p.base_unit, 0) + 1
    dominant_unit = max(unit_counts, key=unit_counts.__getitem__)
    same_unit = [p for p in candidates if p.base_unit == dominant_unit]

    if not same_unit:
        same_unit = candidates

    best_unit = min(same_unit, key=lambda p: p.effective_price_per_base_unit)
    best_total = min(same_unit, key=lambda p: p.price)
    best_practical = _pick_practical(same_unit)

    # Ahorro potencial
    worst_ppu = max(p.effective_price_per_base_unit for p in same_unit)
    best_ppu = best_unit.effective_price_per_base_unit
    savings = None
    if worst_ppu > 0:
        savings = ((worst_ppu - best_ppu) / worst_ppu * 100).quantize(Decimal("0.1"))

    return ComparisonResult(
        base_unit=dominant_unit,
        presentations=sorted(parsed, key=lambda p: p.effective_price_per_base_unit),
        best_unit_value=best_unit,
        best_total_price=best_total,
        best_practical_choice=best_practical,
        savings_vs_worst=savings,
    )


def _pick_practical(candidates: list[PresentationComparison]) -> Optional[PresentationComparison]:
    """
    Heurística de opción práctica:
    - Si hay solo 1, esa es.
    - Si el mejor valor por unidad es también el más barato en total → esa.
    - Si no, elegimos la presentación con mejor precio/unidad
      entre las que NO son la más grande (evitar bulk si no es necesario).
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    sorted_by_ppu = sorted(candidates, key=lambda p: p.effective_price_per_base_unit)
    sorted_by_price = sorted(candidates, key=lambda p: p.price)

    best_ppu = sorted_by_ppu[0]
    cheapest = sorted_by_price[0]

    if best_ppu.offer_id == cheapest.offer_id:
        return best_ppu

    # Elegir la segunda más grande por total_in_base (intermedia)
    sorted_by_size = sorted(candidates, key=lambda p: p.total_in_base)
    mid_idx = max(0, len(sorted_by_size) // 2 - 1)
    return sorted_by_size[mid_idx] if sorted_by_size else best_ppu
