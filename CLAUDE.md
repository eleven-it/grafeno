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

# Reset DB and reload demo (WARNING: drops all data)
python seeds/reset.py

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
├── domain/models.py         # SQLAlchemy ORM models (User, ShoppingList, ShoppingListItem,
│                            #   ProductCanonical, OfferObservation, AlertRule, AlertEvent)
├── domain/enums.py          # All domain enums
├── services/
│   ├── unit_economics.py    # CORE: deterministic price-per-unit calculations
│   ├── matching.py          # Product normalization and similarity scoring
│   ├── recommendation.py    # best_unit_value / best_total_price / best_practical_choice
│   ├── sync_service.py      # Sync offers from connectors; connector registry
│   ├── price_history.py     # Price trend analysis over OfferObservation records
│   ├── alert_service.py     # Rule evaluation and AlertEvent generation
│   ├── canonical_service.py # ProductCanonical CRUD and item-linking
│   ├── offer_service.py     # Offer ingestion (auto-derives unit economics on import)
│   ├── list_service.py
│   └── item_service.py
├── api/
│   ├── routers/             # One file per resource domain
│   └── schemas/             # Pydantic in/out schemas
├── connectors/
│   ├── base.py              # Abstract BaseConnector interface
│   └── mock.py              # Mock data: Carrefour, Walmart, Coto, Easy, Sodimac, MercadoLibre
└── core/                    # Settings (pydantic-settings) + structlog setup
```

## Key Conventions

**Unit economics is the central feature.** `services/unit_economics.py` parses product titles with regex (no LLM), converts to a base unit (L, kg, m, m2, m3, unit), and calculates `price_per_base_unit`. This is called automatically on every `offer_service.import_offer()` — the derived fields are persisted on `OfferObservation`.

**Connectors are pluggeable.** Implement `BaseConnector` (base.py) and register in `sync_service.REGISTRY`. `sync_service.sync_item()` and `sync_service.sync_list()` use the registry to pull and persist offers automatically. The business logic in services never changes when adding a new source.

**Sync is the primary ingestion path** (not `POST /offers/import` which is for manual/external use). Call `POST /lists/{id}/sync` or `POST /items/{id}/sync` to auto-populate offers via the connector registry.

**Recommendations separate three concerns:**
- `best_unit_value`: lowest price per base unit
- `best_total_price`: lowest absolute spend
- `best_practical_choice`: heuristic middle ground (avoid forcing large bulk on user)

**Price history** is built from accumulated `OfferObservation` records — no separate table. `price_history.get_price_history()` groups by source and computes trends.

**Demo user for MVP.** Auth is not implemented yet. `list_service.get_or_create_demo_user()` returns a fixed `demo@grafeno.app` user. All list endpoints operate as this user.

**Tests use SQLite in-memory** via the `db` fixture in `conftest.py`. Unit economics, matching, sync, and price history tests have zero external dependencies (mock connector needs no network).

**JSON columns** (excluded_brands, allowed_stores, installments, raw_attributes) use SQLAlchemy `JSON` in models (SQLite-compatible). Alembic migration uses PostgreSQL `JSONB` explicitly.

## API Surface (v0.2)

| Method | Path | Description |
|--------|------|-------------|
| POST | /lists | Create list |
| GET | /lists | Get all lists |
| GET/PATCH/DELETE | /lists/{id} | List CRUD |
| POST | /lists/{id}/items | Add item |
| GET | /lists/{id}/items | List items |
| PATCH/DELETE | /items/{id} | Item CRUD |
| GET | /items/{id}/offers | Raw offers |
| GET | /items/{id}/unit-economics | Price per unit per offer |
| GET | /items/{id}/comparisons | Alias for unit-economics |
| GET | /items/{id}/recommendation | best_unit_value / best_total_price / best_practical |
| GET | /items/{id}/price-history | Price trend over time by source |
| POST | /lists/{id}/sync | Auto-sync offers from connectors for all items |
| POST | /items/{id}/sync | Auto-sync offers for a single item |
| GET | /sources/search?q= | Search connector without persisting |
| GET | /sources | List available connectors |
| POST | /offers/import | Manual single offer import |
| POST | /offers/import/batch | Manual batch import |
| GET | /lists/{id}/best-cart | Full cart recommendation with store split |
| POST | /alerts/rules | Create alert rule |
| GET | /alerts/rules | List rules |
| GET | /alerts/events | List triggered events |
| POST | /alerts/evaluate/{item_id} | Evaluate alerts for item |
| POST | /alerts/evaluate-list/{list_id} | Evaluate alerts for all items in list |
| POST/GET | /canonicals | Canonical product CRUD |
| POST | /canonicals/items/{id}/link | Link item to canonical product |

## Domain Notes

- `OfferObservation.price_per_base_unit` — always in `normalized_unit` (L, kg, etc.). Never compare across different `normalized_unit` values.
- `ShoppingListItem.allow_equivalents` — when True, `get_comparable_offers()` also fetches offers linked to the same `canonical_product_id`.
- Alert rules are evaluated manually via POST endpoints. Background worker (Celery/Arq) is a v0.3 item.
- `matching.match_score()` returns 0.0–1.0. Sync uses threshold 0.35 by default. ≥ 0.70 means probable match; ≥ 0.85 near-certain.
- Adding a real connector: implement `BaseConnector`, add to `sync_service.REGISTRY`.
