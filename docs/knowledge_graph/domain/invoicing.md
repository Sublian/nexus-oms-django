---
id: domain-invoicing
type: Entity
status: active
owner: operator
last_review: 2026-06-29
tags: [domain, invoicing, sunat, fiscal-compliance]
---

# Invoicing

## ¿Qué es?

La Facturación es el proceso de emisión de comprobantes tributarios ante la autoridad fiscal (SUNAT en Perú), con seguimiento de su aceptación/rechazo y reconciliación.

Consta de:
- **InvoiceSyncQueue**: Cola persistente de facturas en proceso de sincronización con SUNAT
- **Estados en Order**: invoice_status, invoice_external_id, invoice_hash, invoice_attempts, invoice_last_error

Nota: No existe modelo Invoice separado. Los datos de facturación viven en Order y en la cola.

## ¿Por qué existe?

Las facturas son documentos legales requeridos por la ley:
- Cada venta debe facturarse ante SUNAT
- SUNAT debe aceptar o rechazar
- Aceptación genera código de seguridad (hash CDR)
- Rechazos requieren correcciones
- Todo debe registrarse para auditoría

## Estructura

### En Order
- `invoice_status` — PENDING|QUEUED|PROCESSING|SUBMITTED|SYNC_PENDING|SYNC_PROCESSING|ACCEPTED|OBSERVED|REJECTED|RETRYING|FAILED|CANCELLED
- `invoice_external_id` — Identificador asignado por Nubefact ("B001-42")
- `invoice_hash` — Código de seguridad recibido de SUNAT
- `invoice_attempts` — Número de intentos de emisión
- `invoice_last_error` — Último error registrado (max 500 chars)

### InvoiceSyncQueue
- `order` — OneToOneField a Order
- `status` — PENDING|PROCESSING|COMPLETED|FAILED|EXHAUSTED|DEAD_LETTER
- `attempts` — Contador de polls a SUNAT
- `next_retry_at` — Cuándo reintentar (backoff exponencial)
- `locked_at` — Timestamp del lock actual (previene doble polling)
- `last_attempt_at` — Cuándo fue la última consulta
- `last_response` — JSON de respuesta de Nubefact (audit trail)
- `last_error` — Último error de SUNAT
- `completed_at` — Cuándo alcanzó estado terminal
- `exhausted_at` — Cuándo se agotaron reintentos

## Estados FSM (InvoiceSyncQueue)

```
PENDING
  ↓ (sync_single_invoice_task)
PROCESSING
  ↓
COMPLETED  (SUNAT aceptó/observó/rechazó)
  ↓
  FAILED (error permanente de Nubefact)
  ↓
  EXHAUSTED (MAX_ATTEMPTS alcanzado)
  ↓
  DEAD_LETTER (intervención manual)
```

## Invariantes Críticas

- **Idempotencia en Submit**: `get_or_create` en queue previene facturas duplicadas por retries Celery.
- **Lock en Sync**: select_for_update() impide doble polling entre workers.
- **Backoff Exponencial**: Delays entre reintentos aumentan (60s → 5m → 15m → 30m → 1h → 6h → 24h).
- **Estados Terminales Inmutables**: COMPLETED, FAILED, EXHAUSTED no cambian.
- **Kárdex JSON**: last_response guarda respuesta de SUNAT para auditoría.

## Fases

### Fase 1: Submit (Síncrono)
- Order.status = PAID dispara invoice_submit_task
- Envía comprobante a Nubefact
- Nubefact retorna external_id o error
- Si éxito: crea InvoiceSyncQueue(STATUS_PENDING)

### Fase 2: Sync Poll (Asíncrono, Celery Beat)
- sync_pending_invoices_task itera colas PENDING cada 1 min
- Despacha sync_single_invoice_task por cada entrada
- Consulta Nubefact: "¿Qué dijo SUNAT?"
- Reintentos con backoff si SUNAT aún procesando
- Fallo permanente → mark_failed
- Max attempts → mark_exhausted

### Fase 3: Reconciliación
- SUNAT "accepted" → Order.invoice_status = "accepted"
- SUNAT "observed" → Order.invoice_status = "observed"
- SUNAT "rejected" → Order.invoice_status = "rejected"
- InvoiceSyncQueue.mark_completed()

## Relaciones

← [payments.md](./payments.md) — Facturación ocurre post-pago
→ [orders.md](./orders.md) — Estados de facturación viven en Order

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [domain/root.md](./root.md)
