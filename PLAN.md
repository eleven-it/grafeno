# PLAN.md — Grafeno

Plan de producto y técnico. Documenta el estado exacto del sistema, las decisiones tomadas y el roadmap detallado para continuar en cualquier sesión sin contexto previo.

---

## Estado actual: v0.2 (operativo)

**Branch activo:** `claude/add-claude-documentation-Zkbcx`
**Tests:** 62/62 passing
**Último commit:** `6423792` — feat(v0.2): sync engine, price history, canonical products

La API corre con `uvicorn app.main:app --reload`. Requiere PostgreSQL.
Para tests no se necesita DB externa (SQLite in-memory via conftest.py).

---

## Qué está construido

### Infraestructura base
- `requirements.txt`, `.env.example`, `Dockerfile`, `docker-compose.yml`
- `app/core/config.py` — pydantic-settings, lee `.env`
- `app/core/logging.py` — structlog con ConsoleRenderer (dev) / JSONRenderer (prod)
- `app/infrastructure/database.py` — engine SQLAlchemy, `SessionLocal`, `get_db()`
- `alembic.ini` + `alembic/env.py` + `alembic/versions/001_initial_schema.py`
- `pytest.ini` — testpaths=tests, asyncio_mode=strict

### Dominio (`app/domain/`)
- `enums.py` — ListType, ListStatus, MonitoringFrequency, ItemPriority, ItemStatus, AlertRuleType, BaseUnit, SourceType
- `models.py` — 7 modelos SQLAlchemy:
  - `User` — id, email, name
  - `ShoppingList` — user_id, name, description, list_type, country, currency, budget, monitoring_frequency, status
  - `ShoppingListItem` — list_id, original_text, category, preferred_brand, excluded_brands (JSON), desired_presentation, desired_quantity, target_price, priority, allowed_stores (JSON), excluded_stores (JSON), allow_equivalents, allow_bulk, status, canonical_product_id
  - `ProductCanonical` — name, category, base_unit, attributes (JSON)
  - `OfferObservation` — todos los campos de precio + unit economics derivados: parsed_quantity, parsed_unit, parsed_pack_size, total_quantity, normalized_unit, price_per_base_unit
  - `AlertRule` — item_id, rule_type, threshold_value, threshold_unit, is_active
  - `AlertEvent` — rule_id, offer_id, message, acknowledged

> **Nota:** Modelos usan `JSON` (SQLAlchemy genérico, SQLite-compatible). La migración Alembic usa `JSONB` de PostgreSQL explícitamente. No mezclar.

### Servicios (`app/services/`)

| Archivo | Responsabilidad |
|---------|----------------|
| `unit_economics.py` | Parse de presentaciones (regex), conversión a unidad base, cálculo price_per_base_unit, promos (2x1, 3x2, % off), comparación de presentaciones |
| `matching.py` | Normalización de texto (unicode, stopwords), tokenización, scoring Jaccard + categoría + subtipo + marca |
| `offer_service.py` | Ingesta de ofertas; llama unit_economics automáticamente en import |
| `sync_service.py` | Registro de connectors (REGISTRY dict), sync por item o lista, filtrado por excluded_stores/brands, match threshold |
| `recommendation.py` | best_unit_value / best_total_price / best_practical_choice; recommend_item() y recommend_cart() |
| `price_history.py` | Agrupa OfferObservation por source, calcula min/max/tendencia sin tabla extra |
| `alert_service.py` | Evaluación de 5 tipos de reglas: price_below, unit_price_below, price_drop_pct, back_in_stock, better_equivalent |
| `canonical_service.py` | CRUD de ProductCanonical, link item→canonical, búsqueda ILIKE |
| `list_service.py` | CRUD de ShoppingList, get_or_create_demo_user |
| `item_service.py` | CRUD de ShoppingListItem |

### Connectors (`app/connectors/`)
- `base.py` — `BaseConnector` (ABC) con `search()`, `get_offer()`, `RawOffer` dataclass
- `mock.py` — `MockConnector` con 15 ofertas de: Carrefour (leche ×3), Walmart (leche pack, arroz, detergente), Coto (arroz ×3), Easy (pintura ×2), Sodimac (pintura, sin stock), MercadoLibre (leche x12 con installments)

**Para agregar un conector real:** implementar `BaseConnector` → agregar a `sync_service.REGISTRY`.

### API (`app/api/`)
- `deps.py` — `get_db()` generator
- `routers/lists.py` — CRUD listas (5 endpoints)
- `routers/items.py` — CRUD items + offers + unit-economics + comparisons + recommendation (8 endpoints)
- `routers/offers.py` — import single / batch (2 endpoints)
- `routers/sync.py` — sync list, sync item, search sources, list sources (4 endpoints)
- `routers/price_history.py` — GET /items/{id}/price-history (1 endpoint)
- `routers/recommendations.py` — GET /lists/{id}/best-cart (1 endpoint)
- `routers/alerts.py` — rules CRUD + evaluate item + evaluate list (5 endpoints)
- `routers/canonical.py` — CRUD + search + link item (4 endpoints)

**Total: ~30 endpoints.** Ver tabla completa en CLAUDE.md.

### Seeds
- `seeds/demo.py` — crea usuario demo, 2 listas, 4 items, importa las 15 ofertas del mock, crea 2 reglas de alerta. Imprime los IDs para testear.
- `seeds/reset.py` — drop all + create all + demo.py (pide confirmación)

### Tests (62 passing)
| Archivo | Qué cubre |
|---------|-----------|
| `test_unit_economics.py` | Parse de presentaciones, cálculo precio/unidad, promos, comparación (25 tests) |
| `test_matching.py` | Normalización, scoring, find_best_match (10 tests) |
| `test_connectors.py` | MockConnector search/get/to_dict/installments/stock (7 tests) |
| `test_integration.py` | Flujo list→item→offer→recommendation con SQLite (5 tests) |
| `test_sync.py` | sync_item, filtros excluded_stores, sync_list, thresholds (7 tests) |
| `test_price_history.py` | Series por fuente, min/max, best_source, price_change_pct (6 tests) |
| `tests/conftest.py` | Fixture `db` — SQLite in-memory, create/drop all |

---

## Decisiones de diseño tomadas

1. **Sin LLM en el core.** Unit economics y matching son determinísticos. El agente conversacional (OpenClaw) es un cliente externo, no parte del core.

2. **Modelos usan JSON no JSONB en ORM.** JSONB es solo en la migración. Permite tests con SQLite.

3. **Usuario demo fijo para MVP.** `demo@grafeno.app` sin auth. Auth real es v0.3.

4. **Price history sin tabla extra.** Se construye agrupando `OfferObservation`. Si el volumen crece, se puede materializar en una tabla `price_snapshots` en v0.4.

5. **Sync con threshold 0.35 por default.** Conservador para no perder ofertas relevantes. El umbral "casi seguro" es 0.70+.

6. **best_practical_choice heurística.** Elige la presentación de tamaño medio cuando la más grande no es también la más barata. Es intencionalmente simple; mejorar con preferencias de usuario en v0.3.

7. **Alertas evaluadas manualmente.** Worker background es v0.3. La estructura de reglas/eventos ya está lista.

---

## Roadmap detallado

### v0.3 — Auth + Worker + Conector real
**Prioridad: alta. Necesario para salir de demo.**

#### Auth JWT
- Agregar `python-jose[cryptography]`, `passlib[bcrypt]` a requirements
- Nuevo modelo `User` con `hashed_password`
- `POST /auth/register`, `POST /auth/login` → JWT
- Dependency `get_current_user` en `app/api/deps.py`
- Reemplazar `get_or_create_demo_user()` por usuario autenticado
- Todos los endpoints de listas filtrados por `current_user.id`
- **Archivos a crear:** `app/api/routers/auth.py`, `app/api/schemas/auth.py`, `app/core/security.py`

#### Worker de monitoreo (Arq recomendado sobre Celery — más simple, async-native)
- `pip install arq`
- `app/workers/monitor.py` — tarea `sync_all_active_lists(ctx)` que itera listas activas y llama `sync_service.sync_list()`
- `app/workers/alert_worker.py` — tarea `evaluate_all_alerts(ctx)` post-sync
- Scheduler: cada lista tiene `monitoring_frequency` (hourly/daily/weekly) → cron con arq
- **Requiere Redis** (ya en docker-compose opcional)
- **Archivos a crear:** `app/workers/__init__.py`, `app/workers/monitor.py`, `app/workers/scheduler.py`

#### Conector Carrefour Argentina (primer conector real)
- Estrategia: scraping con `httpx` + parsing HTML (Carrefour tiene estructura semiestructurada)
- Alternativa: API pública no documentada (inspeccionar XHR en el sitio)
- `app/connectors/carrefour.py` implementa `BaseConnector`
- Agregar a `sync_service.REGISTRY`
- Rate limiting + retry con backoff exponencial en el conector
- **Archivos a crear:** `app/connectors/carrefour.py`

---

### v0.4 — Matching mejorado + Multi-moneda + Paginación

#### Matching con TF-IDF
- Reemplazar Jaccard simple por TF-IDF sobre corpus de títulos
- `scikit-learn` o implementación liviana propia
- Mantener la interfaz `match_score(title_a, title_b) → MatchResult` sin cambiar callers
- Agregar umbral de confianza por categoría (ej: leche puede tener threshold más bajo que electrónica)
- **Archivo a modificar:** `app/services/matching.py`

#### Paginación
- Todos los endpoints GET que devuelven listas necesitan `limit` + `offset` o cursor
- Respuesta envuelta: `{"items": [...], "total": N, "offset": 0, "limit": 50}`
- **Archivos a modificar:** todos los routers GET con listas

#### Multi-moneda
- Nuevo servicio `app/services/currency.py` con tasas de cambio (hardcoded para MVP, luego API)
- `OfferObservation` ya tiene `currency`; agregar `price_ars` como campo derivado opcional
- Comparaciones siempre en la moneda de la lista (ya tiene `currency`)

#### Price history materializada
- Nueva tabla `price_snapshots` con campos: `offer_observation_id`, `item_id`, `source`, `date` (solo fecha), `min_price`, `max_price`, `close_price`
- Job diario que materializa snapshots
- El endpoint `GET /items/{id}/price-history` lee de snapshots si existen, de observaciones si no
- Nueva migración Alembic: `002_price_snapshots.py`

---

### v0.5 — Notificaciones + Webhooks

#### Push notifications para alertas
- Modelo `UserDevice` (user_id, device_token, platform: ios/android/web)
- Integración Firebase Cloud Messaging (FCM) para mobile
- Webhook URL por usuario para integraciones custom (Slack, etc.)
- `app/services/notification_service.py` — abstracción sobre FCM + webhooks
- Worker Arq: post-evaluación de alertas dispara notificaciones

#### Webhooks salientes
- `POST /webhooks` — registrar URL de webhook para el usuario
- Payload estándar: `{event: "alert_triggered", data: AlertEvent, timestamp}`
- Retry con backoff si el endpoint remoto falla

---

### v1.0 — Producción

#### Seguridad y hardening
- Rate limiting por IP y por usuario (`slowapi`)
- Validación de URLs en `OfferObservation.url` (no SSRF)
- Sanitización de `raw_attributes` (no ejecutar JSON arbitrario)
- Secrets via variables de entorno (nunca hardcoded)
- HTTPS obligatorio en producción

#### Observabilidad
- OpenTelemetry traces en servicios críticos (unit_economics, sync, recommendation)
- Métricas: ofertas importadas/hora, latencia de sync por conector, alertas disparadas
- Health check mejorado: `GET /health` verifica DB + Redis + conectores

#### Escalabilidad
- Connection pooling en PostgreSQL (`pgbouncer` o `asyncpg`)
- Migrar a FastAPI async con `async def` + `asyncpg` si sync se convierte en bottleneck
- Cache Redis para recomendaciones (TTL 5 min por item)

---

## Flujo end-to-end de demo (estado actual)

```bash
# 1. Setup
pip install -r requirements.txt
cp .env.example .env
docker-compose up -d db
alembic upgrade head

# 2. Cargar datos demo
python seeds/demo.py
# → imprime: list_id, item_ids

# 3. Sincronizar ofertas via connector (flujo principal)
curl -X POST localhost:8000/lists/{LIST_ID}/sync

# 4. Comparar precios por unidad
curl localhost:8000/items/{ITEM_ID}/unit-economics
# → [{title, price, price_per_base_unit, label: "$960/L"}, ...]

# 5. Ver recomendación
curl localhost:8000/items/{ITEM_ID}/recommendation
# → {best_unit_value, best_total_price, best_practical_choice}

# 6. Carrito completo con división por tienda
curl localhost:8000/lists/{LIST_ID}/best-cart

# 7. Historial de precios
curl "localhost:8000/items/{ITEM_ID}/price-history?days=30"

# 8. Evaluar alertas
curl -X POST localhost:8000/alerts/evaluate-list/{LIST_ID}
```

---

## Gaps conocidos en v0.2 (no bloqueantes para demo)

| Gap | Impacto | Dónde resolver |
|-----|---------|----------------|
| Sin paginación en endpoints GET | Bajo para demo, alto en producción | v0.4 |
| `best_practical_choice` heurística muy simple | Recomendación a veces no es la mejor | v0.3 con preferencias de usuario |
| Matching Jaccard sensible a variaciones de marca | Falsos negativos en marcas nuevas | v0.4 TF-IDF |
| `canonical_service.search_canonicals` usa ILIKE | No funciona en SQLite (tests) | v0.4: adaptar o mockear en tests |
| Sin validación de `monitoring_frequency` como enum | Acepta strings arbitrarios | Próxima iteración |
| `seeds/demo.py` no es idempotente | Re-ejecutar duplica datos | Próxima iteración: check por email+name |
| Alert `back_in_stock` requiere ≥2 observaciones | Primera vez no dispara | Por diseño, documentar |
| `GET /items/{id}/price-history` falla 404 si hay 0 obs | Podría retornar array vacío | Próxima iteración |

---

## Archivos críticos que no tocar sin entender

| Archivo | Por qué es crítico |
|---------|-------------------|
| `app/services/unit_economics.py` | Motor central; cualquier cambio en regex o factores de conversión rompe precios históricos |
| `app/domain/models.py` | Cambiar columnas requiere nueva migración Alembic |
| `alembic/versions/001_initial_schema.py` | No modificar migraciones ya aplicadas; crear nuevas |
| `app/connectors/base.py` | Cambiar `RawOffer` o `BaseConnector` rompe todos los connectors |
| `app/services/sync_service.py::REGISTRY` | Agregar connectors aquí, no en otro lugar |

---

## Variables de entorno necesarias

```
DATABASE_URL=postgresql://grafeno:grafeno@localhost:5432/grafeno
SECRET_KEY=change-me-in-production
ENVIRONMENT=development   # o production
LOG_LEVEL=INFO
# Futuro v0.3:
# REDIS_URL=redis://localhost:6379/0
# FCM_SERVER_KEY=...
```
