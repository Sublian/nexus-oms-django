---
id: domain-payments
type: Entity
status: active
owner: operator
last_review: 2026-06-29
tags: [domain, payments, transactions, fees]
---

# Payments

## ¿Qué es?

Un Pago (Payment) es el registro del método y monto de efectivo recibido por una orden, incluyendo comisiones deducidas por pasarelas de pago.

Responde: ¿Cuánto dinero se recibió, de qué forma, con qué comisión?

## ¿Por qué existe?

Los pagos cierran la transacción comercial y alimentan finanzas:
- Efectivo: ¿Dinero ingresó realmente?
- Comisiones: ¿Qué porcentaje dedujo la pasarela?
- Métodos: ¿Tarjeta, transferencia, efectivo?
- Referencia: ¿Trace ID de la pasarela externa?
- Reconciliación: Pago vs. Factura vs. Orden

## Estructura

### Relación con Orden
- `order` — OneToOneField a Order
- Una orden, un pago máximo

### Información de Pago
- `method` — CASH | CARD | TRANSFER | WALLET
- `amount` — Monto total cobrado (Order.total_amount)
- `transaction_reference` — Trace ID de pasarela (ej. confirmación Niubiz)
- `fee_amount` — Comisión deducida (ej. 3.5% si CARD, 0 si CASH)
- `payment_date` — Cuándo se registró

### Cálculos Derivados
- `net_amount` — amount - fee_amount (dinero neto recibido)

## Comisiones

Configuradas en `PaymentFeeConfig` por tenant (valores por defecto):

```
CASH      → 0%
CARD      → 3.5%
TRANSFER  → 0%
WALLET    → 1%   (Yape/Plin)
```

Comisión se calcula **en el momento del pago** (`fee_amount = amount × rate / 100`,
redondeo `ROUND_HALF_UP`), no es dinámico. `net_amount = amount - fee_amount`.
El `fee_rate` se snapshotea en cada Payment; cambiar la config no altera pagos históricos.

## Invariantes Críticas

- **OneToOne**: Un Payment por Order. No hay múltiples pagos vigentes.
  - Excepción: un pago `declined`/`failed` se elimina al reintentar (sin historial de intentos).
- **Amount Fijo**: Equals Order.total_amount. No hay sobrepago ni sub-pago parcial.
- **Fee Determinístico**: Calculado al crear el pago; depende del método y la config del tenant.
- **Transacción Atómica**: Crear Payment y cambiar Order.status = PAID ocurren juntos o nada.
- **Transición Guardada**: `Order.status` solo pasa a PAID si `PAID ∈ VALID_TRANSITIONS[order.status]`
  (ADR-005 F2). Un pago aprobado de una orden cancelada NO la revive: el payment queda `approved`
  y se loguea la anomalía.
- **Contexto Auto-gestionado**: `PaymentService` setea su propio contexto de tenant (ADR-005 F1);
  funciona desde el worker de Celery sin middleware.
- **Pagos Pendientes**: TRANSFER/WALLET quedan `pending` y se confirman contra la pasarela
  (manual en dashboard/API o auto por `sync_single_payment_task` cada 60s).

## Relaciones

← [orders.md](./orders.md) — Payment cierra el ciclo de venta
→ [invoicing.md](./invoicing.md) — Post-pago, la orden se factura

## Flujo Post-Pago

Cuando Payment se crea (CASH/CARD aprobado inmediato):
1. Order.status cambia a PAID (solo si la transición es válida)
2. OrderWorkflowService.handle_order_paid() se dispara
3. Flujos subsiguientes: facturación, notificaciones, etc.

Para TRANSFER/WALLET, la orden sigue PENDING hasta que `confirm_payment` aprueba.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-08-09  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [invoicing.md](./invoicing.md)
