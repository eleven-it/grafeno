# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Python 3.11** + **FastAPI** + **SQLAlchemy 2.x** + **PostgreSQL** + **Alembic**
- Pydantic v2 for schemas, structlog for structured logging
- pytest + SQLite in-memory for tests (no external DB needed for unit/integration tests)

## Commands

```bash
# Install
pip install -r requirements.txt

# Run DB migrations
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "description"

# Start API (dev)
uvicorn app.main:app --reload

# Load demo data (requires DB running)
python seeds/demo.py

# Tests (no DB required)
pytest

# Single test
pytest tests/test_unit_economics.py::TestParsePresentation::test_multipack_6x1L -v

# Coverage
pytest --cov=app --cov-report=term-missing
```

## Architecture

```
app/
├── domain/models.py      # SQLAlchemy ORM models (User, ShoppingList, ShoppingListItem,
│                         #   ProductCanonical, OfferObservation, AlertRule, AlertEvent)
├── domain/enums.py       # All domain enums
├── services/
│   ├── unit_economics.py # CORE: deterministic price-per-unit calculations
│   ├── matching.py       # Product normalization and similarity scoring
│   ├── recommendation.py # best_unit_value / best_total_price / best_practical_choice
│   ├── alert_service.py  # Rule evaluation and AlertEvent generation
│   ├── offer_service.py  # Offer ingestion (auto-derives unit economics on import)
│   ├── list_service.py
│   └── item_service.py
├── api/
│   ├── routers/          # One file per resource domain
│   └── schemas/          # Pydantic in/out schemas
├── connectors/
│   ├── base.py           # Abstract BaseConnector interface
│   └── mock.py           # Mock data: Carrefour, Walmart, Coto, Easy, Sodimac, MercadoLibre
└── core/                 # Settings (pydantic-settings) + structlog setup
```

## Key Conventions

**Unit economics is the central feature.** `services/unit_economics.py` parses product titles with regex (no LLM), converts to a base unit (L, kg, m, m2, m3, unit), and calculates `price_per_base_unit`. This is called automatically on every `offer_service.import_offer()` — the derived fields are persisted on `OfferObservation`.

**Connectors are pluggeable.** Implement `BaseConnector` (base.py) and call `offer_service.import_offer()` with the `RawOffer.to_dict()`. The business logic in services never changes when adding a new source.

**Recommendations separate three concerns:**
- `best_unit_value`: lowest price per base unit
- `best_total_price`: lowest absolute spend
- `best_practical_choice`: heuristic middle ground (avoid forcing large bulk on user)

**Demo user for MVP.** Auth is not implemented yet. `list_service.get_or_create_demo_user()` returns a fixed `demo@grafeno.app` user. All list endpoints operate as this user.

**Tests use SQLite in-memory** via the `db` fixture in `conftest.py`. Unit economics and matching tests have zero external dependencies.

**JSONB columns** (excluded_brands, allowed_stores, installments, raw_attributes) store lists/dicts. SQLAlchemy maps them as Python lists/dicts.

## Domain Notes

- `OfferObservation.price_per_base_unit` — always in the `normalized_unit` (L, kg, etc.). Never compare across different `normalized_unit` values.
- `ShoppingListItem.allow_equivalents` — when True, `get_comparable_offers()` also fetches offers linked to the same `canonical_product_id`.
- Alert rules are evaluated manually via `POST /alerts/evaluate/{item_id}`. A background worker (Celery/Arq) is a v0.2 item.
- `matching.match_score()` returns 0.0–1.0. Threshold ≥ 0.70 means probable match; ≥ 0.85 near-certain.
