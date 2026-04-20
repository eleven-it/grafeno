"""
Tests del motor de matching y normalización.
"""
import pytest
from app.services.matching import (
    normalize_text,
    tokenize,
    parse_product,
    match_score,
    find_best_match,
)


class TestNormalize:
    def test_lowercase(self):
        assert normalize_text("Leche ENTERA") == "leche entera"

    def test_accents_removed(self):
        assert normalize_text("Aceite Oliva Clásico") == "aceite oliva clasico"

    def test_special_chars_removed(self):
        assert "%" not in normalize_text("Leche 0% grasa")

    def test_multiple_spaces_collapsed(self):
        result = normalize_text("Leche   Entera   1L")
        assert "  " not in result


class TestMatchScore:
    def test_identical_titles_high_score(self):
        result = match_score("Leche Entera 1L", "Leche Entera 1L")
        assert result.score >= 0.85

    def test_same_product_different_presentation(self):
        # Mismo producto, distinta presentación → score medio
        result = match_score("Leche Entera 500ml", "Leche Entera 1L")
        assert result.score >= 0.50

    def test_different_category_low_score(self):
        result = match_score("Leche Entera 1L", "Detergente Magistral 500ml")
        assert result.score < 0.3

    def test_different_brand_penalizes(self):
        result_same = match_score("Leche Sancor 1L", "Leche Sancor 5L")
        result_diff = match_score("Leche Sancor 1L", "Leche Serenísima 1L")
        # Diferente marca debe tener menor score
        assert result_same.score >= result_diff.score

    def test_leche_variants_match(self):
        """Distintas formas de escribir el mismo producto."""
        variants = [
            "Leche entera 1L",
            "Leche Entera x 1000cc",
            "Leche Entera 1 Lt",
        ]
        for a in variants:
            for b in variants:
                if a != b:
                    result = match_score(a, b)
                    # Todos deberían tener score razonablemente alto
                    assert result.score >= 0.4, f"Score bajo entre '{a}' y '{b}': {result.score}"


class TestFindBestMatch:
    CANDIDATES = [
        {"id": "1", "title": "Leche Entera La Serenísima 1L"},
        {"id": "2", "title": "Detergente Magistral 500ml"},
        {"id": "3", "title": "Arroz Gallo 1kg"},
    ]

    def test_finds_leche(self):
        result = find_best_match("leche 1 litro", self.CANDIDATES)
        assert result is not None
        assert result["id"] == "1"

    def test_finds_detergente(self):
        result = find_best_match("detergente 500ml", self.CANDIDATES)
        assert result is not None
        assert result["id"] == "2"

    def test_returns_none_when_no_match(self):
        result = find_best_match("smartphone samsung galaxy", self.CANDIDATES, threshold=0.8)
        assert result is None
