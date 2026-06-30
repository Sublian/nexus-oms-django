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

```
Si method = CARD:
  fee = amount × 3.5%
Si method = CASH / TRANSFER / WALLET:
  fee = 0
```

Comisión se calcula **en el momento del pago**, no es dinámico.

## Invariantes Críticas

- **OneToOne**: Un Payment por Order. No hay múltiples pagos.
- **Amount Fijo**: Equals Order.total_amount. No hay sobrepago ni sub-pago parcial.
- **Fee Determinístico**: Depende solo del método. No varía por monto.
- **Transacción Atómica**: Crear Payment y cambiar Order.status = PAID ocurre juntos o nada.
- **Registro Inmutable**: Una vez creado, Payment no se edita. Devoluciones son OrderReturn, no reembolsos de Payment.

## Relaciones

← [orders.md](./orders.md) — Payment cierra el ciclo de venta
→ [invoicing.md](./invoicing.md) — Post-pago, la orden se factura

## Flujo Post-Pago

Cuando Payment se crea:
1. Order.status cambia a PAID
2. OrderWorkflowService.handle_order_paid() se dispara
3. Flujos subsiguientes: facturación, notificaciones, etc.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [invoicing.md](./invoicing.md)
