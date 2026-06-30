---
id: architecture-payment-pipeline
type: Domain
status: active
owner: operator
last_review: 2026-06-29
tags: [architecture, payments, transactions]
---

# Payment Pipeline

## ¿Qué es?

El Payment Pipeline es el proceso mediante el cual un cliente registra el método y monto de pago para una orden, marcando la orden como PAID y orquestando el flujo post-pago (facturación, auditoría).

## ¿Por qué existe?

Los pagos cierran la transacción comercial. Este pipeline garantiza que:
- El pago se registra con método y referencia clara
- Las comisiones de pasarela se descuentan apropiadamente
- El cambio de estado dispara la orquestación post-pago
- Todo ocurre en un contexto transaccional

## Flujo Conceptual

```
Orden en estado PENDING (creada, sin pago)
    ↓
Usuario solicita pagar (desde dashboard)
    ↓
Valida: ¿PAID es transición válida desde estado actual?
    ↓
Valida: ¿Stock sigue siendo suficiente? (sanity check)
    ↓
Lee método de pago y referencia de transacción (POST)
    ↓
Calcula comisión (si CARD: 3.5%, sino 0)
    ↓
Crea Payment:
  - order (OneToOneField)
  - method (CASH/CARD/TRANSFER/WALLET)
  - amount (Order.total_amount)
  - fee_amount (comisión)
  - transaction_reference (rastreo externo)
    ↓
Cambia Order.status = PAID
    ↓
Ordena flujo post-pago:
  OrderWorkflowService.handle_order_paid(order)
  ↓
  - Emite factura (invoice_submit_task)
  - Envía notificaciones
    ↓
Persiste Order
    ↓
Retorna: modalidad éxito
```

## Componentes Involucrados

| Componente | Responsabilidad |
|---|---|
| Payment | Modelo que almacena método, monto, fee, referencia |
| Order | Transición de estado PENDING → PAID |
| OrderWorkflowService | Orquesta post-pago (facturación, notificaciones) |
| Order FSM | Valida transiciones permitidas |
| NotificationService | Envía confirmación al cliente |

## Invariantes Críticas

- **Validación de Transición**: No todos los estados permiten → PAID. FSM lo valida.
- **Fee Determinístico**: Comisión es 3.5% de total si método es CARD, sino 0.
- **OneToOne Payment**: Una orden, un pago. `get_or_create` previene duplicados.
- **Transacionalidad**: Todo sucede en una transacción atómica. Fallo del workflow aborta el cambio de estado.
- **Registro Síncrono**: Payment se crea inmediatamente. El workflow post-pago es asíncrono.

## Relaciones

← [sales_pipeline.md](./sales_pipeline.md) — Orden debe existir y estar en estado transicionable  
→ [invoice_pipeline.md](./invoice_pipeline.md) — Post-pago dispara facturación  
→ [reporting_pipeline.md](./reporting_pipeline.md) — Pagos se consolidan en reportes  

## ¿Qué sigue?

Una vez registrado el pago, la orden entra en [invoice_pipeline.md](./invoice_pipeline.md) para ser emitida ante SUNAT.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [reporting_pipeline.md](./reporting_pipeline.md)
