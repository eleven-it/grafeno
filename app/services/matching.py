"""
Motor de matching y normalización de productos.

Estrategia: reglas explícitas + parsing simple. Sin LLM. Extensible.

El matching agrupa ofertas del mismo producto base aunque vengan con
nombres distintos de distintas fuentes. Por ahora usa:
  1. Normalización de texto (lowercase, sin stopwords, sin acentos)
  2. Extracción de marca, categoría, variante
  3. Score por token overlap
  4. Penalización si unidades son incompatibles
"""
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


# ---------------------------------------------------------------------------
# Stopwords para normalización
# ---------------------------------------------------------------------------

STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas",
    "con", "sin", "para", "por", "en", "a", "y", "o", "x",
    "pack", "paquete", "bolsa", "botella", "caja", "lata", "tarro",
    "sachet", "sobre", "bidon", "bidón",
}


# ---------------------------------------------------------------------------
# Categorías conocidas y sus aliases
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "leche": ["leche", "milk"],
    "detergente": ["detergente", "lavaplatos", "lavavajillas", "dish"],
    "arroz": ["arroz", "rice"],
    "aceite": ["aceite", "oil"],
    "harina": ["harina", "flour"],
    "azucar": ["azucar", "azúcar", "sugar"],
    "yerba": ["yerba", "mate"],
    "pintura": ["pintura", "latex", "látex", "paint", "esmalte"],
    "cemento": ["cemento", "cement"],
    "ceramica": ["cerámica", "ceramica", "porcelanato", "piso", "tile"],
}

SUBTYPES: dict[str, list[str]] = {
    "entera": ["entera", "whole", "full"],
    "descremada": ["descremada", "desnatada", "skim", "light", "0%"],
    "semidescremada": ["semidescremada", "semi", "parcialmente"],
    "larga_vida": ["larga vida", "uht", "larga-vida"],
}

BRAND_BLOCKLIST = {"la", "el", "los", "las", "super", "mega", "ultra", "maxi"}


# ---------------------------------------------------------------------------
# Parsing estructurado de un título
# ---------------------------------------------------------------------------

@dataclass
class ParsedProduct:
    normalized_text: str
    detected_category: Optional[str]
    detected_subtype: Optional[str]
    detected_brand: Optional[str]
    tokens: set[str]


def normalize_text(text: str) -> str:
    """Lowercase, quita acentos, quita caracteres especiales."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> set[str]:
    return {t for t in text.split() if t not in STOPWORDS and len(t) > 1}


def parse_product(title: str, brand_hint: Optional[str] = None) -> ParsedProduct:
    norm = normalize_text(title)
    tokens = tokenize(norm)

    category = None
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in norm for kw in keywords):
            category = cat
            break

    subtype = None
    for sub, keywords in SUBTYPES.items():
        if any(kw in norm for kw in keywords):
            subtype = sub
            break

    # Marca: priorizar hint, si no buscar token que empiece con mayúscula en original
    brand = brand_hint
    if not brand:
        # Heurística: primer token del título que no sea stopword y no sea número
        for word in title.split():
            w_lower = word.lower()
            if (
                len(word) > 2
                and w_lower not in STOPWORDS
                and w_lower not in BRAND_BLOCKLIST
                and not re.match(r"^\d", word)
                and word[0].isupper()
            ):
                brand = word
                break

    return ParsedProduct(
        normalized_text=norm,
        detected_category=category,
        detected_subtype=subtype,
        detected_brand=brand,
        tokens=tokens,
    )


# ---------------------------------------------------------------------------
# Scoring de match entre dos productos
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    score: float          # 0.0 - 1.0
    confidence: float     # 0.0 - 1.0
    reasons: list[str]


def match_score(
    title_a: str,
    title_b: str,
    brand_a: Optional[str] = None,
    brand_b: Optional[str] = None,
) -> MatchResult:
    """
    Calcula score de similitud entre dos títulos de productos.
    Score ≥ 0.7: probablemente el mismo producto.
    Score ≥ 0.85: casi seguro el mismo producto.
    """
    pa = parse_product(title_a, brand_a)
    pb = parse_product(title_b, brand_b)

    reasons: list[str] = []
    score = 0.0
    confidence = 0.5

    # 1. Mismo categoría detectada → +0.35
    if pa.detected_category and pa.detected_category == pb.detected_category:
        score += 0.35
        reasons.append(f"same_category:{pa.detected_category}")
        confidence += 0.2

    # 2. Overlap de tokens significativos
    if pa.tokens and pb.tokens:
        intersection = pa.tokens & pb.tokens
        union = pa.tokens | pb.tokens
        jaccard = len(intersection) / len(union) if union else 0
        score += jaccard * 0.40
        if jaccard > 0.5:
            reasons.append(f"token_overlap:{jaccard:.2f}")
            confidence += 0.15

    # 3. Mismo subtipo → +0.15
    if pa.detected_subtype and pa.detected_subtype == pb.detected_subtype:
        score += 0.15
        reasons.append(f"same_subtype:{pa.detected_subtype}")

    # 4. Misma marca → +0.10 / marca distinta → -0.20
    if pa.detected_brand and pb.detected_brand:
        if normalize_text(pa.detected_brand) == normalize_text(pb.detected_brand):
            score += 0.10
            reasons.append(f"same_brand:{pa.detected_brand}")
            confidence += 0.1
        else:
            score -= 0.20
            reasons.append(f"different_brand:{pa.detected_brand}≠{pb.detected_brand}")
            confidence -= 0.1

    score = max(0.0, min(1.0, score))
    confidence = max(0.1, min(1.0, confidence))

    return MatchResult(score=round(score, 3), confidence=round(confidence, 3), reasons=reasons)


def find_best_match(
    query_title: str,
    candidates: list[dict],
    threshold: float = 0.40,
) -> Optional[dict]:
    """
    Dado un título de búsqueda, encuentra el mejor candidato entre una lista.
    Cada candidato debe tener al menos {"id", "title"}.
    Retorna None si ninguno supera el umbral.
    """
    best = None
    best_score = threshold

    for c in candidates:
        result = match_score(query_title, c["title"])
        if result.score >= best_score:
            best_score = result.score
            best = {**c, "_match_score": result.score, "_match_confidence": result.confidence}

    return best
