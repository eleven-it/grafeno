# Grafeno

Plataforma de seguimiento inteligente de compras multi-canal. Compara precios, monitorea ofertas y recomienda la mejor compra por producto, presentación y lista — en supermercados, retail y marketplaces.

---

## Visión del sistema

Grafeno es un **agente de compras** que permite a un usuario crear listas de productos para seguimiento y recibir recomendaciones sobre dónde y cuándo conviene comprar.

La arquitectura está diseñada para que:
- El **backend sea el core del negocio** (source of truth)
- El **motor de unit economics** opere de forma determinística, sin LLM
- Un agente conversacional (OpenClaw u otro) consuma la API como cliente externo
- Los conectores de fuentes sean **pluggeables** — se agregan sin tocar el core

---

## Arquitectura

```
app/
├── domain/          # Modelos SQLAlchemy + enums (sin lógica de negocio)
├── services/        # Lógica de negocio pura
│   ├── unit_economics.py    # Parser de presentaciones + cálculo precio/unidad
│   ├── matching.py          # Normalización y matching de productos
│   ├── recommendation.py    # Motor de recomendaciones
│   ├── alert_service.py     # Evaluación de reglas y generación de eventos
│   ├── list_service.py
│   ├── item_service.py
│   └── offer_service.py
├── api/
│   ├── routers/     # FastAPI routers (una ruta por recurso)
│   └── schemas/     # Pydantic schemas (validación + serialización)
├── connectors/      # Adaptadores de fuentes externas
│   ├── base.py      # Interfaz abstracta BaseConnector
│   └── mock.py      # Datos demo: Carrefour, Walmart, Coto, Easy, Sodimac, MercadoLibre
└── core/            # Config, logging estructurado
```

### Flujo de datos

```
[Fuente externa / Mock connector]
        ↓
POST /offers/import  →  offer_service.import_offer()
                              ↓
                    unit_economics.calculate_unit_economics()
                              ↓
                    OfferObservation (price_per_base_unit derivado)
                              ↓
GET /items/{id}/recommendation  →  recommendation.recommend_item()
                              ↓
                    ComparisonResult { best_unit_value, best_total_price, best_practical }
```

### Unit economics

Las unidades soportadas y sus bases de comparación:

| Categoría | Unidades de entrada | Base |
|-----------|-------------------|------|
| Volumen   | ml, cc, cl, L, litros | L |
| Peso      | mg, g, gr, kg, tn | kg |
| Largo     | mm, cm, m | m |
| Área      | cm2, m2 | m2 |
| Volumen sólido | cm3, m3 | m3 |
| Unidades  | unit, und, pza, unidad | unit |

Ejemplo:
```
Leche 500 ml  = $700  → $1400/L
Leche 1 L     = $1100 → $1100/L
Leche Bidón 5L= $4800 → $960/L  ← mejor valor por litro
```

---

## Cómo correrlo

### Requisitos
- Python 3.11+
- PostgreSQL 14+ (o Docker)

### Setup local

```bash
# 1. Clonar e instalar dependencias
git clone https://github.com/eleven-it/grafeno.git
cd grafeno
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configurar entorno
cp .env.example .env
# Editar DATABASE_URL si es necesario

# 3. Levantar base de datos (con Docker)
docker-compose up -d db

# 4. Correr migraciones
alembic upgrade head

# 5. Cargar datos demo
python seeds/demo.py

# 6. Levantar API
uvicorn app.main:app --reload
```

La API estará en `http://localhost:8000`
Documentación interactiva: `http://localhost:8000/docs`

### Con Docker Compose (todo)

```bash
docker-compose up --build
```

---

## Cómo testearlo

```bash
# Todos los tests
pytest

# Solo unit economics (sin DB)
pytest tests/test_unit_economics.py -v

# Solo matching
pytest tests/test_matching.py -v

# Solo integración (SQLite en memoria)
pytest tests/test_integration.py -v

# Con cobertura
pytest --cov=app --cov-report=term-missing

# Un test específico
pytest tests/test_unit_economics.py::TestParsePresentation::test_multipack_6x1L -v
```

---

## Endpoints principales

### Listas

```bash
# Crear lista
curl -X POST http://localhost:8000/lists \
  -H "Content-Type: application/json" \
  -d '{"name": "Super semanal", "list_type": "recurrent", "currency": "ARS"}'

# Listar
curl http://localhost:8000/lists

# Detalle
curl http://localhost:8000/lists/{list_id}

# Actualizar
curl -X PATCH http://localhost:8000/lists/{list_id} \
  -H "Content-Type: application/json" \
  -d '{"status": "archived"}'
```

### Items

```bash
# Agregar item a lista
curl -X POST http://localhost:8000/lists/{list_id}/items \
  -H "Content-Type: application/json" \
  -d '{
    "original_text": "leche entera 1L",
    "category": "leche",
    "preferred_brand": "La Serenísima",
    "desired_quantity": 3,
    "priority": "high",
    "allow_bulk": true
  }'

# Listar items de una lista
curl http://localhost:8000/lists/{list_id}/items
```

### Ofertas

```bash
# Importar oferta individual
curl -X POST http://localhost:8000/offers/import \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "{item_id}",
    "source": "carrefour",
    "retailer": "Carrefour",
    "title": "Leche Entera La Serenísima 1 L",
    "price": 1100,
    "currency": "ARS",
    "in_stock": true
  }'

# Importar batch
curl -X POST http://localhost:8000/offers/import/batch \
  -H "Content-Type: application/json" \
  -d '{
    "offers": [
      {"item_id": "{item_id}", "source": "carrefour", "title": "Leche 500 ml", "price": 700, "currency": "ARS", "in_stock": true},
      {"item_id": "{item_id}", "source": "walmart", "title": "Leche Bidon 5 L", "price": 4800, "currency": "ARS", "in_stock": true}
    ]
  }'
```

### Unit Economics y Comparaciones

```bash
# Ver precio por litro / kilo / unidad de cada oferta
curl http://localhost:8000/items/{item_id}/unit-economics

# Respuesta de ejemplo:
# [
#   {"title": "Leche 500 ml", "price": 700, "base_unit": "L",
#    "price_per_base_unit": 1400.0, "label": "$1400.0000/L"},
#   {"title": "Leche 1 L", "price": 1100, "base_unit": "L",
#    "price_per_base_unit": 1100.0, "label": "$1100.0000/L"},
#   {"title": "Leche Bidon 5 L", "price": 4800, "base_unit": "L",
#    "price_per_base_unit": 960.0, "label": "$960.0000/L"}
# ]
```

### Recomendaciones

```bash
# Recomendacion para un item especifico
curl http://localhost:8000/items/{item_id}/recommendation
# Responde: best_unit_value, best_total_price, best_practical_choice

# Mejor carrito completo para toda una lista
curl http://localhost:8000/lists/{list_id}/best-cart
```

### Alertas

```bash
# Crear regla: alertar si precio baja de $900
curl -X POST http://localhost:8000/alerts/rules \
  -H "Content-Type: application/json" \
  -d '{"item_id": "{item_id}", "rule_type": "price_below", "threshold_value": 900, "threshold_unit": "ARS"}'

# Tipos: price_below | price_drop_pct | back_in_stock | better_equivalent | unit_price_below

# Ver alertas disparadas
curl http://localhost:8000/alerts/events

# Evaluar alertas manualmente para un item
curl -X POST http://localhost:8000/alerts/evaluate/{item_id}
```

---

## Conectores de fuentes

Para agregar un nuevo retailer, implementar `BaseConnector`:

```python
# app/connectors/mi_retailer.py
from app.connectors.base import BaseConnector, RawOffer

class MiRetailerConnector(BaseConnector):
    @property
    def source_id(self) -> str:
        return "mi_retailer_ar"

    @property
    def source_type(self) -> str:
        return "supermarket"

    def search(self, query: str, **kwargs) -> list[RawOffer]:
        # Scraping / API call real
        ...

    def get_offer(self, external_sku: str) -> RawOffer | None:
        ...
```

El conector devuelve `RawOffer`. El servicio `offer_service.import_offer()` persiste y calcula unit economics automáticamente.

---

## Roadmap

### v0.2
- [ ] Worker Celery/Arq para monitoreo periodico automatico
- [ ] Webhooks / notificaciones push para alertas
- [ ] Historial de precios con timeseries
- [ ] Conector real Carrefour Argentina (scraper con playwright o API publica)

### v0.3
- [ ] Auth JWT (usuarios reales, multiples listas por usuario)
- [ ] Canonical products management (admin endpoint)
- [ ] Fuzzy matching mejorado con TF-IDF o embeddings
- [ ] Soporte multi-moneda con conversion automatica

### v1.0
- [ ] Dashboard web (Next.js o similar)
- [ ] App mobile (React Native)
- [ ] ML para deteccion automatica de categorias y marcas

---

## Future OpenClaw Integration

OpenClaw (o cualquier agente conversacional) consume esta API como herramientas. El backend es source of truth; el agente interpreta y presenta — no calcula.

### Tools conceptuales

**`createShoppingList`** → `POST /lists`
```json
{ "name": "Super semanal", "list_type": "recurrent", "currency": "ARS" }
```

**`addTrackedProduct`** → `POST /lists/{list_id}/items`
```json
{ "original_text": "leche entera 1L", "preferred_brand": "La Serenísima", "desired_quantity": 3 }
```

**`comparePresentations`** → `GET /items/{item_id}/unit-economics`
Devuelve lista ordenada por `price_per_base_unit` con `label` legible (`$960/L`).

**`findBestOffer`** → `GET /items/{item_id}/recommendation`
Devuelve `best_unit_value`, `best_total_price`, `best_practical_choice` con `reasoning` pre-generado.

**`getBestCart`** → `GET /lists/{list_id}/best-cart`
Recomendacion por item + division por tienda + total estimado.

**`subscribeDealAlerts`** → `POST /alerts/rules`
```json
{ "item_id": "...", "rule_type": "price_below", "threshold_value": 1000 }
```

### Ejemplo de conversacion

```
Usuario: "Quiero seguir el precio de la leche entera, avisame si baja de $1000"

OpenClaw:
  1. addTrackedProduct("leche entera 1L")       → item_id
  2. comparePresentations(item_id)              → muestra opciones con precio/L
  3. subscribeDealAlerts(item_id, price_below, 1000)
  → "Listo. Mejor precio hoy: $960/L en el bidon de 5L (Carrefour).
     Te aviso cuando baje de $1000/L."
```

Las respuestas incluyen `reasoning`, `label` y campos `best_*` con suficiente contexto para que el agente no necesite razonar sobre los datos — solo interpretar y comunicar.
