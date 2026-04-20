"""
Tests del motor de unit economics. Sin dependencias de DB.
Verifican la lógica central de parsing y cálculo de precio por unidad.
"""
import pytest
from decimal import Decimal
from app.services.unit_economics import (
    parse_presentation,
    calculate_unit_economics,
    compare_presentations,
    _apply_promo,
)


class TestParsePresentation:
    def test_simple_volume_liters(self):
        p = parse_presentation("Leche Entera 1 L")
        assert p is not None
        assert p.quantity == Decimal("1")
        assert p.base_unit == "L"
        assert p.total_in_base == Decimal("1")

    def test_volume_ml_converted(self):
        p = parse_presentation("Leche 500 ml")
        assert p is not None
        assert p.base_unit == "L"
        assert p.total_in_base == Decimal("0.5")

    def test_volume_5L_bidon(self):
        p = parse_presentation("Leche Entera Bidón 5 L")
        assert p is not None
        assert p.total_in_base == Decimal("5")

    def test_multipack_6x1L(self):
        p = parse_presentation("Pack 6 x 1 L")
        assert p is not None
        assert p.pack_size == 6
        assert p.total_in_base == Decimal("6")

    def test_multipack_6x1L_no_space(self):
        p = parse_presentation("Leche 6x1L")
        assert p is not None
        assert p.pack_size == 6
        assert p.total_in_base == Decimal("6")

    def test_multipack_with_ml(self):
        p = parse_presentation("Pack 3 x 750 ml")
        assert p is not None
        assert p.pack_size == 3
        assert p.total_in_base == Decimal("2.25")   # 3 * 0.75L

    def test_weight_grams(self):
        p = parse_presentation("Arroz 500 g")
        assert p is not None
        assert p.base_unit == "kg"
        assert p.total_in_base == Decimal("0.5")

    def test_weight_kg(self):
        p = parse_presentation("Arroz 5 kg")
        assert p is not None
        assert p.total_in_base == Decimal("5")

    def test_area_m2(self):
        p = parse_presentation("Piso Cerámico 1.5 m2")
        assert p is not None
        assert p.base_unit == "m2"
        assert p.total_in_base == Decimal("1.5")

    def test_no_unit_returns_none(self):
        p = parse_presentation("Algo sin medida")
        assert p is None

    def test_cc_alias_for_ml(self):
        """1000cc = 1L"""
        p = parse_presentation("Leche 1000cc")
        assert p is not None
        assert p.base_unit == "L"
        assert p.total_in_base == Decimal("1")


class TestCalculateUnitEconomics:
    def test_leche_500ml(self):
        ue = calculate_unit_economics(Decimal("700"), "Leche 500 ml")
        assert ue is not None
        assert ue.price_per_base_unit == Decimal("1400.0000")  # 700/0.5L = 1400/L

    def test_leche_1L(self):
        ue = calculate_unit_economics(Decimal("1100"), "Leche 1 L")
        assert ue is not None
        assert ue.price_per_base_unit == Decimal("1100.0000")

    def test_leche_5L(self):
        ue = calculate_unit_economics(Decimal("4800"), "Leche Bidón 5 L")
        assert ue is not None
        assert ue.price_per_base_unit == Decimal("960.0000")

    def test_promo_10pct_off(self):
        ue = calculate_unit_economics(
            Decimal("1280"), "Detergente 750 ml", promo_description="10% off"
        )
        assert ue is not None
        # precio efectivo = 1280 * 0.9 = 1152
        assert ue.effective_price == Decimal("1152.00")

    def test_promo_2x1(self):
        ue = calculate_unit_economics(
            Decimal("1100"), "Leche 1 L", promo_description="2x1"
        )
        assert ue is not None
        # precio efectivo = 550 para 1L → 550/L
        assert ue.effective_price == Decimal("550.00")
        assert ue.effective_price_per_base_unit == Decimal("550.0000")


class TestApplyPromo:
    def test_2x1(self):
        result = _apply_promo(Decimal("1000"), "2x1 en toda la línea")
        assert result == Decimal("500.00")

    def test_3x2(self):
        result = _apply_promo(Decimal("900"), "3x2 aprovechá")
        assert result == Decimal("600.00")

    def test_percent_off(self):
        result = _apply_promo(Decimal("1000"), "25% off")
        assert result == Decimal("750.00")

    def test_no_promo(self):
        result = _apply_promo(Decimal("1000"), None)
        assert result == Decimal("1000")


class TestComparePresentations:
    """
    Caso clásico: leche en distintas presentaciones.
    Esperado: 5L es el mejor valor unitario, 500ml es el menor desembolso.
    """
    OFFERS = [
        {"offer_id": "a", "title": "Leche 500 ml", "source": "carrefour",
         "price": 700, "currency": "ARS", "in_stock": True},
        {"offer_id": "b", "title": "Leche 1 L", "source": "carrefour",
         "price": 1100, "currency": "ARS", "in_stock": True},
        {"offer_id": "c", "title": "Leche Bidón 5 L", "source": "carrefour",
         "price": 4800, "currency": "ARS", "in_stock": True},
    ]

    def test_best_unit_value_is_5L(self):
        result = compare_presentations(self.OFFERS)
        assert result is not None
        assert result.best_unit_value.offer_id == "c"   # 960/L

    def test_best_total_price_is_500ml(self):
        result = compare_presentations(self.OFFERS)
        assert result.best_total_price.offer_id == "a"  # $700

    def test_savings_calculated(self):
        result = compare_presentations(self.OFFERS)
        assert result.savings_vs_worst is not None
        # 500ml = 1400/L, 5L = 960/L → ahorro ~31%
        assert result.savings_vs_worst > Decimal("30")

    def test_presentations_sorted_by_ppu(self):
        result = compare_presentations(self.OFFERS)
        ppus = [p.price_per_base_unit for p in result.presentations]
        assert ppus == sorted(ppus)

    def test_out_of_stock_excluded_from_best(self):
        offers_with_oos = [
            {"offer_id": "a", "title": "Leche 500 ml", "source": "carrefour",
             "price": 700, "currency": "ARS", "in_stock": True},
            {"offer_id": "b", "title": "Leche 5 L", "source": "carrefour",
             "price": 1, "currency": "ARS", "in_stock": False},  # mejor precio pero sin stock
        ]
        result = compare_presentations(offers_with_oos)
        # best_unit_value debe ser la que tiene stock
        assert result.best_unit_value.offer_id == "a"
