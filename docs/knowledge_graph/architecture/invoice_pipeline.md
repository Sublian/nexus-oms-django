---
id: architecture-invoice-pipeline
type: Domain
status: active
owner: operator
last_review: 2026-06-29
tags: [architecture, invoicing, sunat, async-sync]
---

# Invoice Pipeline

## ¿Qué es?

El Invoice Pipeline es el proceso de emisión y sincronización de comprobantes tributarios con la autoridad fiscal (SUNAT en Perú) a través del proveedor Nubefact.

Consta de tres fases: emisión (submit a Nubefact), sincronización (poll a SUNAT via Nubefact), y reconciliación (marca estado final).

## ¿Por qué existe?

Las facturas son documentos legales. Este pipeline garantiza que:
- Cada orden se emite ante SUNAT con identidad de la organización
- Se maneja reintentos y timeouts de forma robusta
- Los estados de SUNAT se sincronizan continuamente
- Los fallos se registran sin bloquear transacciones comerciales

## Flujo Conceptual

```
Orden → Estado PAID
    ↓
Fase 1: Submit Invoice (Síncrono)
  invoice_submit_task()
  ↓
  Llama Nubefact.submit_invoice()
  ↓
  ÉXITO: Order.invoice_external_id = "B001-42"
         Crea InvoiceSyncQueue(STATUS_PENDING)
  ↓
  FALLO: Order.invoice_status = "failed"
         Order.invoice_last_error = "..."

Fase 2: Sync Poll (Asíncrono, Celery Beat)
  sync_pending_invoices_task (cada 1 min)
  ↓
  Itera InvoiceSyncQueue.STATUS_PENDING donde next_retry_at ≤ now()
  ↓
  Para cada entry:
    sync_single_invoice_task(entry_id)
    ↓
    Lock DB (select_for_update)
    Llama InvoiceStatusQueryUseCase.execute(entry)
    ↓
    RESULT: Consulta a Nubefact → SUNAT status

Fase 3: Reconciliación (basada en RESULT)
  Estado SUNAT = "accepted"  → Order.invoice_status = "accepted"
                                InvoiceSyncQueue.mark_completed()
                ↓
  Estado SUNAT = "observed"  → Order.invoice_status = "observed"
                                InvoiceSyncQueue.mark_completed()
                ↓
  Estado SUNAT = "rejected"  → Order.invoice_status = "rejected"
                                InvoiceSyncQueue.mark_completed()
                ↓
  Estado SUNAT = "processing" → Schedule retry (backoff exponencial)
                                 next_retry_at = now() + delay
                ↓
  Error temporal (5xx/timeout) → Reschedule, no marcar failed
                ↓
  Error permanente (4xx/sin config) → mark_failed, no reintentar
                ↓
  MAX_ATTEMPTS alcanzado     → mark_exhausted, requeire intervención
```

## Componentes Involucrados

| Componente | Responsabilidad |
|---|---|
| Order | Almacena invoice_status, invoice_external_id, invoice_hash, invoice_attempts, invoice_last_error |
| InvoiceSyncQueue | Cola persistente de sincronizaciones pendientes con SUNAT |
| Nubefact (external) | API que emite y sincroniza con SUNAT |
| invoice_submit_task | Celery task que emite la factura |
| sync_pending_invoices_task | Celery Beat (scheduler) que barre colas |
| sync_single_invoice_task | Celery task que sincroniza una entrada |
| InvoiceStatusQueryUseCase | Lógica de negocio: parsea respuesta SUNAT |

## Invariantes Críticas

- **Idempotencia**: Multiple retries de Celery no generan facturas duplicadas. `get_or_create` en cola.
- **Lock DB en Sync**: select_for_update() impide doble polling entre workers.
- **Backoff Exponencial**: Delays entre reintentos aumentan (60s, 5m, 15m, ..., 24h).
- **Estado Inmutable**: Estados terminales (accepted/rejected/exhausted) no se cambian.
- **Responsabilidad Separada**: Submit es síncrono (tarea). Sync es asíncrono (polling).

## Relaciones

← [payment_pipeline.md](./payment_pipeline.md) — Facturación ocurre post-pago  
→ [reporting_pipeline.md](./reporting_pipeline.md) — Reportes consolidan estados de facturación  

## ¿Qué sigue?

Una vez reconciliada (aceptada o rechazada por SUNAT), la orden queda en estado final para [reporting_pipeline.md](./reporting_pipeline.md).

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [payment_pipeline.md](./payment_pipeline.md)
