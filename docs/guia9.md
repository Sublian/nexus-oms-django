# guia9.md — Sprint 3 Paso 4 + Mini-Sprint Operational Visibility
## Estado: junio 2026

---

## CONTEXTO — DÓNDE ESTAMOS

| Sprint | Estado | Fecha |
|--------|--------|-------|
| Sprint 1 | ✅ COMPLETO | CompanyInvoiceConfig + MockClient + UseCase |
| Sprint 2 | ✅ COMPLETO | 17 mayo 2026 — lock + idempotencia + Celery + NubefactClient real |
| FASE 2A Dashboard | ✅ COMPLETO | KPIs operacionales con drill-down |
| Sprint 3 Pasos 1-3 | ✅ COMPLETO | InvoiceSyncQueue model + sync_single_invoice_task + polling worker |
| **Sprint 3 Paso 4** | 🔜 PENDIENTE | Conectar create_invoice_task → InvoiceSyncQueue |

---

## SPRINT 3 — PASO 4: CONECTAR TASK → QUEUE

### Objetivo

Cuando `create_invoice_task` termina exitosamente con `invoice_status='submitted'` y `external_id` válido,
debe crear automáticamente el registro en `InvoiceSyncQueue`.

Esto cierra el ciclo operacional async completo:

```
Order PAID
  ↓
create_invoice_task
  ↓
NubefactClient → submitted (external_id válido)
  ↓
InvoiceSyncQueue  ← ESTE ES EL PASO 4
  ↓
sync_pending_invoices_task (polling)
  ↓
Estado final: accepted | rejected | observed
```

### Restricciones de implementación

1. **Solo crear queue item si** `invoice_status == 'submitted'`
   — No encolar en `processing`, `retrying`, ni `failed`

2. **Evitar duplicados** — máximo 1 item activo por order
   — Usar `get_or_create` con constraint de unicidad

3. **Idempotencia** — retries de Celery no deben crear registros duplicados

4. **Herencia de tenant** — el `InvoiceSyncQueue` item hereda `organization` del Order

5. **Logs estructurados obligatorios**:
   ```
   [InvoiceQueue][order_id=X][tenant_id=Y][provider=Z][action=ENQUEUED|DUPLICATE_PREVENTED]
   ```

6. **Placeholders de métricas** (para futura integración):
   ```python
   # metrics.increment("queue.created")
   # metrics.increment("queue.duplicate_prevented")
   # metrics.increment("queue.creation_failed")
   ```

### Implementación — dónde insertar el código

Dentro de `create_invoice_task`, al final del bloque de éxito:

```python
# Al terminar con invoice_status = 'submitted'
with transaction.atomic():
    queue_item, created = InvoiceSyncQueue.objects.get_or_create(
        order=order,
        status__in=["pending", "processing"],
        defaults={
            "status": "pending",
            "next_retry_at": timezone.now() + timedelta(minutes=1),
            "organization": order.organization,
        }
    )

    if created:
        logger.info(
            f"[InvoiceQueue][order_id={order.id}][tenant_id={order.organization_id}]"
            f"[action=ENQUEUED][queue_id={queue_item.id}]"
        )
    else:
        logger.info(
            f"[InvoiceQueue][order_id={order.id}][action=DUPLICATE_PREVENTED]"
            f"[existing_queue_id={queue_item.id}]"
        )
```

### Tests requeridos

- ✅ Task exitosa → crea InvoiceSyncQueue item
- ✅ Doble ejecución → solo 1 queue item (idempotencia)
- ✅ Task fallida (permanent) → NO crea queue item
- ✅ organization se hereda correctamente del Order

---

## MINI-SPRINT: OPERATIONAL VISIBILITY

Después de cerrar el Paso 4, antes de cualquier dashboard complejo:

### 1. Django Admin mínimo

```python
# billing/admin.py
@admin.register(InvoiceSyncQueue)
class InvoiceSyncQueueAdmin(admin.ModelAdmin):
    list_display = ["order", "status", "attempts", "next_retry_at", "created_at"]
    list_filter = ["status", "organization", "created_at"]
    search_fields = ["order__id"]

@admin.register(CompanyInvoiceConfig)
class CompanyInvoiceConfigAdmin(admin.ModelAdmin):
    list_display = ["organization", "provider_type", "enabled"]
    list_filter = ["provider_type", "enabled"]
```

### 2. UI mínima en order_list

Agregar badge visual de `invoice_status` en la lista de órdenes:

```
| Orden #123 | PAID | ● submitted  |  ...  |
| Orden #124 | PAID | ✅ accepted  |  ...  |
| Orden #125 | PAID | ❌ failed     |  ...  |
```

Colores sugeridos:
- `pending` → gris
- `processing` → amarillo
- `submitted` → azul
- `accepted` → verde
- `rejected` / `failed` → rojo
- `retrying` → naranja

### 3. Sección facturación en order_detail_modal

Agregar tab o sección colapsable en el modal de detalle:

```
FACTURACIÓN
  Estado:        submitted
  External ID:   F001-00001234
  Intentos:      2
  Último error:  — (ninguno)
  Creado:        13 Jun 2026 14:32
```

---

## INVARIANTES A RESPETAR (NO NEGOCIABLES)

Estos invariantes deben mantenerse en todo el código de Sprint 3 en adelante:

1. **issued ≠ accepted** — Un asiento contable solo se puede generar cuando `invoice_status='accepted'`
2. **Lock corto** — El `select_for_update()` solo abarca el chequeo de estado, no la llamada HTTP
3. **Un solo item activo** por order en InvoiceSyncQueue
4. **Multi-tenant always** — Todo modelo hereda TenantModel; todo query respeta TenantManager

---

## ESTADO DE CAMPOS EN Order (post migration 0009)

```python
# Workflow
workflow_processed   BooleanField   default=False
workflow_status      CharField      pending | processing | completed | failed

# Invoice
invoice_status       CharField      pending | processing | submitted | accepted |
                                    rejected | observed | retrying | failed
invoice_external_id  CharField      null=True
invoice_attempts     IntegerField   default=0
invoice_last_error   TextField      null=True
```

---

## LO QUE VIENE DESPUÉS (NO IMPLEMENTAR AÚN)

### Sprint 4 — Operational Dashboard
- Vista por tenant: emitidas, pendientes, rechazadas, retrying, inconsistentes
- Botón "Reprocesar factura" (retry manual)
- Filtros en InvoiceSyncQueue Admin: tenant, estado, aging

### Sprint 5 — Hardening SaaS
- Rate limiting por tenant (evitar que tenant A consuma todos los workers)
- Dead letter queue (facturas imposibles de reconciliar)
- Snapshot de config al momento de emisión (`invoice_config_snapshot`)
- Circuit breaker si Nubefact cae

### Dirección arquitectónica futura
- **Integration Layer**: modelo centralizado de proveedores externos por tenant
  (Nubefact, SUNAT, email, WhatsApp, payment gateways)
- **Accounting Domain**: AccountingEntry + AccountingEntryLine + Ledger
  Regla: solo generar cuando `invoice_status='accepted'`

---

## PRINCIPIO GENERAL

El sistema ya dejó de ser CRUD.
Es una plataforma distribuida multi-tenant de consistencia eventual.

El ciclo debe cerrarse en este orden:
1. Estabilizar pipeline async completo (Paso 4 + Operational Visibility)
2. Luego — y solo luego — construir dashboards y analytics

**No iniciar Sprint 4 hasta que el Paso 4 esté testeado y en main.**
