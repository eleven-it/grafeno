# AGENT.md — Guía de integración para agentes IA

Este documento es para agentes IA (OpenClaw, Claude, GPT, etc.) que consumen la API de Grafeno.
La API base es `http://localhost:8000`. En producción reemplazar por la URL correspondiente.

---

## Qué hace Grafeno

Grafeno es un motor de seguimiento de precios multi-canal. Permite:
- Crear listas de productos a seguir
- Comparar el mismo producto en distintas tiendas y presentaciones
- Calcular el precio por unidad económica (precio/litro, precio/kilo, etc.)
- Recomendar cuál es la mejor compra según distintos criterios
- Disparar alertas cuando baja el precio o aparece un equivalente más barato

**Regla fundamental:** Grafeno hace todos los cálculos. El agente interpreta y comunica. Nunca calcules precios por unidad en el prompt — usa los endpoints de unit-economics y recommendation.

---

## Modelo mental

```
Usuario dice algo → Agente traduce a llamadas API → Grafeno calcula → Agente interpreta respuesta → Responde al usuario
```

Un usuario opera siempre en el contexto de una **lista**. Cada lista tiene **items**. Cada item tiene **ofertas** observadas desde distintas fuentes. Sobre esas ofertas se calculan comparaciones, recomendaciones y alertas.

---

## Flujo típico de una sesión

### 1. Crear o encontrar la lista del usuario

```
GET /lists
```
Si el usuario no tiene listas, crear una:
```
POST /lists
{"name": "Super semanal", "list_type": "recurrent", "currency": "ARS"}
```
Guardar el `id` de la lista — se necesita en casi todos los pasos siguientes.

---

### 2. Agregar un producto a seguir

Cuando el usuario dice *"quiero seguir el precio de la leche entera"*:

```
POST /lists/{list_id}/items
{
  "original_text": "leche entera 1L",
  "category": "leche",
  "desired_quantity": 2,
  "allow_equivalents": true,
  "allow_bulk": true
}
```

Campos opcionales útiles:
- `preferred_brand`: "La Serenísima" — si el usuario prefiere una marca
- `excluded_brands`: ["Genérico"] — marcas a ignorar
- `target_price`: 1000 — precio objetivo para alertas
- `priority`: "high" | "medium" | "low"
- `allowed_stores`: ["carrefour", "walmart"] — solo estas tiendas
- `excluded_stores`: ["easy"] — ignorar estas tiendas

Guardar el `id` del item devuelto.

---

### 3. Sincronizar precios desde las fuentes

Después de agregar items, poblar sus ofertas:

```
POST /lists/{list_id}/sync
```

Esto busca en todos los conectores disponibles y persiste las ofertas que hacen match con los items. Es la forma principal de ingresar datos — no usar `POST /offers/import` a menos que se integre una fuente externa específica.

Para sincronizar un solo item:
```
POST /items/{item_id}/sync
```

Para explorar sin persistir (útil para responder "¿cuánto cuesta X?"):
```
GET /sources/search?q=leche entera
```

---

### 4. Comparar precios por unidad

```
GET /items/{item_id}/unit-economics
```

Respuesta típica:
```json
[
  {
    "offer_id": "...",
    "title": "Leche 500 ml",
    "price": 700,
    "currency": "ARS",
    "base_unit": "L",
    "price_per_base_unit": 1400.0,
    "label": "$1400.0000/L"
  },
  {
    "title": "Leche 1 L",
    "price": 1100,
    "base_unit": "L",
    "price_per_base_unit": 1100.0,
    "label": "$1100.0000/L"
  },
  {
    "title": "Leche Bidón 5 L",
    "price": 4800,
    "base_unit": "L",
    "price_per_base_unit": 960.0,
    "label": "$960.0000/L"
  }
]
```

Cómo comunicarlo al usuario:
> "Encontré 3 presentaciones de leche entera:
> - 500 ml a $700 → **$1.400/L**
> - 1 L a $1.100 → **$1.100/L**
> - Bidón 5 L a $4.800 → **$960/L** ← mejor valor"

---

### 5. Pedir una recomendación

```
GET /items/{item_id}/recommendation
```

Respuesta:
```json
{
  "item_id": "...",
  "item_text": "leche entera 1L",
  "best_unit_value": {
    "title": "Leche Bidón 5 L",
    "source": "carrefour",
    "price": 4800,
    "price_per_base_unit": 960.0,
    "base_unit": "L",
    "reasoning": "Menor precio por L: $960.0/L"
  },
  "best_total_price": {
    "title": "Leche 500 ml",
    "source": "carrefour",
    "price": 700,
    "reasoning": "Menor desembolso total: $700 ARS"
  },
  "best_practical_choice": {
    "title": "Leche 1 L",
    "source": "carrefour",
    "price": 1100,
    "reasoning": "Mejor equilibrio entre precio y practicidad"
  },
  "savings_vs_worst_pct": 31.4,
  "all_offers_count": 5,
  "comparable_offers_count": 3
}
```

**Cómo interpretar para el usuario:**
- `best_unit_value`: conveniene económica máxima (puede requerir comprar más volumen)
- `best_total_price`: para quien quiere gastar lo menos posible ahora
- `best_practical_choice`: para la mayoría de los casos — buen equilibrio
- `savings_vs_worst_pct`: cuánto se ahorra comprando bien vs comprando la peor opción

---

### 6. Ver el mejor carrito para toda una lista

```
GET /lists/{list_id}/best-cart
```

Devuelve recomendación por item + división por tienda:
```json
{
  "list_name": "Super semanal",
  "total_best_price": 7840,
  "currency": "ARS",
  "best_store_split": [
    {
      "store": "carrefour",
      "subtotal": 5900,
      "items": [{"item_text": "leche entera 1L", "price": 1100}, ...]
    },
    {
      "store": "walmart",
      "subtotal": 1940,
      "items": [...]
    }
  ]
}
```

---

### 7. Crear una alerta de precio

Cuando el usuario dice *"avisame si la leche baja de $1000"*:

```
POST /alerts/rules
{
  "item_id": "{item_id}",
  "rule_type": "price_below",
  "threshold_value": 1000,
  "threshold_unit": "ARS"
}
```

Tipos de alerta disponibles:

| rule_type | threshold_value | Cuándo dispara |
|-----------|----------------|----------------|
| `price_below` | precio absoluto (ej: 1000) | precio < umbral |
| `unit_price_below` | precio por unidad base (ej: 900) | precio/L < umbral |
| `price_drop_pct` | porcentaje (ej: 10) | bajó X% desde última observación |
| `back_in_stock` | (no necesario) | volvió a haber stock |
| `better_equivalent` | precio máximo aceptable | hay equivalente más barato que ese precio |

Evaluar alertas (normalmente corre automático, pero se puede forzar):
```
POST /alerts/evaluate/{item_id}
POST /alerts/evaluate-list/{list_id}
```

Ver alertas disparadas:
```
GET /alerts/events
GET /alerts/events?item_id={item_id}
```

---

## Referencia rápida de endpoints

### Listas
```
POST   /lists                          Crear lista
GET    /lists                          Ver todas las listas
GET    /lists/{id}                     Detalle de lista
PATCH  /lists/{id}                     Actualizar (name, status, budget, etc.)
DELETE /lists/{id}                     Eliminar
```

### Items
```
POST   /lists/{list_id}/items          Agregar item
GET    /lists/{list_id}/items          Ver items de una lista
PATCH  /items/{id}                     Actualizar item (status, target_price, etc.)
DELETE /items/{id}                     Eliminar item
```

### Precios y comparaciones
```
GET    /items/{id}/offers              Todas las ofertas crudas del item
GET    /items/{id}/unit-economics      Precio por unidad base de cada oferta
GET    /items/{id}/comparisons         Alias de unit-economics
GET    /items/{id}/recommendation      Recomendación (best_unit_value / best_total / best_practical)
GET    /items/{id}/price-history       Evolución de precios en el tiempo (default últimos 30 días)
GET    /lists/{id}/best-cart           Carrito óptimo para toda la lista
```

### Sincronización y búsqueda
```
POST   /lists/{id}/sync                Sincronizar ofertas para toda la lista
POST   /items/{id}/sync                Sincronizar ofertas para un item
GET    /sources/search?q={query}       Buscar en conectores sin persistir
GET    /sources                        Ver conectores disponibles
```

### Alertas
```
POST   /alerts/rules                   Crear regla de alerta
GET    /alerts/rules                   Ver reglas (opcional: ?item_id=)
GET    /alerts/events                  Ver alertas disparadas (opcional: ?item_id=)
POST   /alerts/evaluate/{item_id}      Evaluar alertas para un item
POST   /alerts/evaluate-list/{list_id} Evaluar alertas para toda una lista
```

### Importación manual (para fuentes externas, no para uso conversacional)
```
POST   /offers/import                  Importar una oferta individual
POST   /offers/import/batch            Importar múltiples ofertas
```

### Productos canónicos (para agrupar equivalentes)
```
POST   /canonicals                     Crear producto canónico
GET    /canonicals                     Listar (opcional: ?category=, ?q=)
POST   /canonicals/items/{id}/link     Vincular item con canónico
```

---

## Ejemplos de conversaciones con respuestas API

### "¿Dónde conviene comprar leche esta semana?"

1. `GET /lists` → obtener lista activa del usuario
2. Buscar el item "leche" en los items de esa lista. Si no existe:
   - `POST /lists/{id}/items` con `original_text: "leche entera"`
   - `POST /items/{item_id}/sync`
3. `GET /items/{item_id}/recommendation`
4. Responder usando `best_practical_choice.reasoning` + `savings_vs_worst_pct`

---

### "Compará la leche de 500ml con la de 1L y la de 5L"

1. `GET /items/{item_id}/unit-economics`
2. Mostrar la tabla con `title`, `price`, `label` (precio/L) ordenada por `price_per_base_unit`
3. Señalar cuál es la más conveniente y el ahorro potencial

---

### "Agregá detergente a mi lista y avisame si baja de $800"

1. `GET /lists` → obtener `list_id` activo
2. `POST /lists/{list_id}/items` con `original_text: "detergente"`, `target_price: 800`
3. `POST /items/{item_id}/sync`
4. `POST /alerts/rules` con `rule_type: "price_below"`, `threshold_value: 800`
5. Confirmar al usuario: item creado + alerta activa + mejor precio actual encontrado

---

### "¿Cuánto bajó el precio de la leche este mes?"

1. `GET /items/{item_id}/price-history?days=30`
2. Para cada serie en `series[]`:
   - `price_change_pct` → si es negativo, bajó; si es positivo, subió
   - `min_price` y `max_price` del período
3. Comunicar: "En Carrefour bajó 4.5% (de $1.100 a $1.050). En Walmart estuvo estable."

---

### "Armá el carrito más barato para mi lista del super"

1. `GET /lists` → encontrar lista de supermercado
2. `POST /lists/{list_id}/sync` → actualizar precios
3. `GET /lists/{list_id}/best-cart`
4. Presentar `best_store_split`: qué comprar en cada tienda y el total

---

## Manejo de casos especiales

### Sin ofertas para un item
Si `all_offers_count == 0` en `/recommendation`, decirle al usuario que no hay precios disponibles y sugerir hacer sync:
```
POST /items/{item_id}/sync
```

### Unidades no comparables
Si `price_per_base_unit` es `null` en un item de `/unit-economics`, significa que no se pudo parsear la presentación del título. Mostrar solo el precio absoluto y aclarar que no hay comparación por unidad disponible.

### Item fuera de stock
Las ofertas sin stock (`in_stock: false`) aparecen en la lista pero **no** se incluyen en `best_unit_value`, `best_total_price` ni `best_practical_choice`. Si solo hay ofertas sin stock, `best_*` puede ser `null`. Comunicar al usuario que el producto no tiene stock disponible.

### Pausar seguimiento de un item
```
PATCH /items/{item_id}
{"status": "paused"}
```
Los items pausados no se sincronizan en `POST /lists/{id}/sync`.

### Marcar un item como comprado
```
PATCH /items/{item_id}
{"status": "purchased"}
```

---

## Lo que Grafeno NO hace (no preguntes)

- No ejecuta compras ni tiene integración con checkout
- No tiene scraping masivo en tiempo real (los conectores del MVP son mocks; los reales se agregan por separado)
- No tiene autenticación de usuarios en v0.2 (todos operan como `demo@grafeno.app`)
- No envía notificaciones automáticas todavía (las alertas se evalúan manualmente o por worker)
- No compara productos de categorías radicalmente distintas (electrónica vs alimentos)

---

## Errores comunes y qué hacer

| Error HTTP | Causa probable | Acción |
|-----------|----------------|--------|
| 404 en `/items/{id}/recommendation` | Item no encontrado | Verificar `item_id` con `GET /lists/{list_id}/items` |
| 404 en `/items/{id}/price-history` | Sin observaciones de precio | Hacer `POST /items/{id}/sync` primero |
| `best_unit_value: null` en recommendation | Sin ofertas con stock | Hacer sync y verificar stock |
| `price_per_base_unit: null` en unit-economics | Título no parseable | El sistema no pudo extraer cantidad/unidad del título de la oferta |
| 422 Unprocessable Entity | Payload inválido | Verificar campos requeridos según esquema |
