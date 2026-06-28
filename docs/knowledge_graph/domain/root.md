# Domain Root — Nexus OMS Business Rules

## ¿Qué es?

Núcleo de lógica de negocio: máquina de estados de órdenes, pipeline de facturación fiscal, gestión de stock, y reglas financieras.

## Order Lifecycle (FSM)

**Máquina principal** (`Order.status`):
```
DRAFT
  ├→ PENDING (validar)
  ├→ COURTESY (sin costo)
  └→ CANCELLED

PENDING
  ├→ PAID (cobro)
  └→ CANCELLED

PAID
  ├→ SHIPPED (envío)
  └→ CANCELLED

SHIPPED
  ├→ DELIVERED (confirmado)
  └→ RETURNED (devolución)

DELIVERED   [terminal]
CANCELLED   [terminal]
RETURNED    [terminal]
```

**Implementación**: `django-fsm` con decoradores `@transition` en `Order` model.

**Archivos**: `src/domain/models/sales.py`, `src/domain/models/order_constants.py`

---

## Invoice Lifecycle (Paralelo, Ortogonal)

**Máquina secundaria** (`Order.invoice_status`): **11 estados**, ortogonal a `status`.

```
pending
  ├→ processing (enviando a SUNAT)
  └→ failed (error permanente)

processing
  ├→ submitted (en cola SUNAT)
  ├→ observed (requiere validación)
  ├→ failed (validación falló)
  ├→ dead_letter (no recoverable)
  └→ exhausted (reintentos agotados)

submitted
  ├→ accepted (✅ SUNAT aceptó)
  ├→ rejected (SUNAT rechazó)
  ├→ observed (requiere review)
  └→ failed (error en transacción)

[terminal states]
accepted   → AccountingEntry creada
rejected   → Manual review requerido
failed     → Retry con backoff
dead_letter → Escalación requerida
exhausted  → Manual intervention
```

**Invariante**: Una orden puede estar `DELIVERED` pero con `invoice_status = FAILED`. Son independientes.

---

## Pipeline de Facturación (3 Fases)

### Fase 1: Disparador (Síncrono)
Cuando `Order.status` → `PAID`:
```python
OrderWorkflowService.handle_order_paid(order)
  → create_invoice_task.delay(order.id)  # async dispatch
```

### Fase 2: Creación (Celery Task)
```python
CreateInvoiceUseCase.execute(order)
  → select_for_update()  # pessimistic lock
  → NubefactClient.create_invoice(order)  # HTTP POST
  → save invoice_external_id + mark invoice_status='processing'
```

**Guards**:
1. `order.invoice_external_id` existe → SKIP (ya creada)
2. `order.invoice_status == 'processing'` → SKIP (otro worker en vuelo)
3. `select_for_update()` → lock atomic

### Fase 3: Sincronización (Celery Beat c/60s)
```python
sync_pending_invoices_task()
  → scan InvoiceSyncQueue
  → fan-out de sync_single_invoice_task
  → InvoiceStatusQueryUseCase.execute(sync_entry)
    → Nubefact/SUNAT: ¿estado de factura?
    → Si accepted → create AccountingEntry
    → Si rejected → mark como rejected
    → Si temporal error → backoff exponencial
```

**Backoff**: `[60, 300, 900, 1800, 3600, 21600, 86400]` segundos

---

## Stock Management

**Ajuste automático vía Django signals**:

1. **Venta** (`OrderItem` created):
   ```
   adjust_stock_on_sale → 
     select_for_update(Product.stock) → 
     stock -= qty → 
     create StockMovement(OUTPUT)
   ```

2. **Compra** (`PurchaseOrder` status → RECEIVED):
   ```
   update_stock_on_received_po → 
     select_for_update() → 
     stock += qty → 
     create StockMovement(INPUT)
   ```

3. **Devolución** (`OrderReturn` reentered_to_stock=True):
   ```
   handle_stock_on_return → 
     select_for_update() → 
     stock += qty → 
     create StockMovement(RETURN)
   ```

**Invariante**: Toda mutación via `select_for_update()` para evitar race conditions.

**Archivo**: `src/domain/signals.py`

---

## Financial Services

### Exchange Rate Chain
```
get_current_rate(date):
  1. Busca ExchangeRate en DB (cache hoy)
  2. Si no → APIMigoClient.get_exchange_rate(hoy)
  3. Si APIMigo falla → intenta ayer
  4. Fallback hardcodeado: 3.80 venta / 3.75 compra (USD)
```

**Riesgo**: Fallback asume tipo de cambio estable (impreciso en volatilidad).

### COGS Estimation
```
get_net_margin_report():
  → Busca último PurchaseOrderItem.unit_cost para producto
  → Si no existe → usa fallback 50% del precio de venta (arbitrario)
```

**Tensión**: Dos servicios (`finance_service.py` + `order_service.py`) duplican esta lógica.

---

## Invariantes Críticas de Dominio

```
1. TRANSICIONES FSM:  Usar @transition decorators, nunca asignar directo
2. INVOICE DEDUP:     select_for_update() → check external_id + status
3. WORKFLOW ONCE:     order.workflow_processed = True es canonical
4. STOCK ATOMIC:      Toda mutación en transacción DB real
5. ACCOUNTING GATE:   AccountingEntry solo si invoice_status='accepted'
6. TENANT FILTER:     TenantManager aplica automáticamente
7. SIGNAL ASYNC:      Los signals no pueden asumir transacción explícita
```

---

## Tensiones Activas (Domain)

| Tensión | Severidad |
|---------|-----------|
| COGS fallback 50% impreciso en reportes | Alta |
| Duplicación finance_service / order_service | Media |
| Sin circuit breaker para APIMigo | Media |
| Fallback exchange-rate asume estabilidad | Media |

---

## Relaciones

- [Architecture](../architecture/root.md) — Stack que ejecuta estas reglas
- [Infrastructure](../infrastructure/root.md) — Persistencia + async que respaldan dominio
- [Security](../security/root.md) — Cómo se protegen estas transiciones

---

**Estado**: STABLE (reglas consolidadas)
**Última actualización**: 2026-06-27
**Responsable**: Tech Lead
**Siguiente nodo recomendado**: [infrastructure/root.md](../infrastructure/root.md)
