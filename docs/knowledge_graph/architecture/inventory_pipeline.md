---
id: architecture-inventory-pipeline
type: Domain
status: active
owner: operator
last_review: 2026-06-29
tags: [architecture, inventory, stock, signals]
---

# Inventory Pipeline

## ¿Qué es?

El Inventory Pipeline es el mecanismo reactivo que ajusta el inventario disponible cuando ocurren transacciones comerciales: ventas (descuento), compras (ingreso), devoluciones (re-ingreso).

Cada movimiento de stock se registra en un Kárdex (auditoría) inmutable.

## ¿Por qué existe?

El inventario es crítico:
- Debe permanecer sincronizado con ventas en tiempo real
- Cada cambio requiere auditoría (quién, cuándo, por qué)
- Validaciones previas evitan sobreventa
- Signals Django realizan descuentos de forma automática y transaccional

## Flujo Conceptual

```
Preventa: Validación Previa
  OrderService.create_order()
  ↓
  ¿Stock.quantity >= item.quantity para cada item?
  NO → raise ValueError, transacción abortada
  SÍ → continuar creación

Venta: Descuento Reactivo (Signal)
  OrderItem.objects.create()
  ↓ (Django signal post_save)
  adjust_stock_on_sale
  ↓
  stock.quantity -= item.quantity
  StockMovement.create(OUTPUT, "Venta: Pedido #X")
  ↓
  Guardado con select_for_update (lock DB)

Devolución: Re-ingreso
  OrderReturn.objects.create(reentered_to_stock=True)
  ↓ (Django signal post_save)
  handle_stock_on_return
  ↓
  stock.quantity += return.quantity
  StockMovement.create(RETURN, "Devolución: Ticket #X")

Compra: Ingreso
  PurchaseOrder.status = RECEIVED
  ↓ (Django signal post_save)
  update_stock_on_received_po
  ↓
  para cada item:
    stock.quantity += po_item.quantity
    StockMovement.create(INPUT, "Compra: OC #X")
```

## Componentes Involucrados

| Componente | Responsabilidad |
|---|---|
| OrderService | Valida stock antes de crear venta (prevención) |
| Stock | Modelo que almacena quantity |
| StockMovement | Auditoría inmutable de cada cambio (Kárdex) |
| Signals (3 handlers) | Descuentan/ingresan stock automáticamente |
| select_for_update() | Lock DB para evitar condiciones de carrera |

## Invariantes Críticas

- **Validación ANTES de Creación**: Stock se verifica antes de crear OrderItem. Si insuficiente, transacción se revierte completamente.
- **Descuento DESPUÉS de Creación**: Signal se dispara cuando item se persiste. No puede fallar silenciosamente.
- **Lock Durante Cambio**: select_for_update() impide condiciones de carrera entre workers simultáneos.
- **Kárdex Inmutable**: Cada StockMovement registra el histórico. Nunca se modifica, solo se crea.
- **Permitir Negativos**: El código permite stock negativo en la BD (no hay validación). Esto es intencional para auditoría, pero debería evitarse con validaciones.

## Relaciones

← [sales_pipeline.md](./sales_pipeline.md) — Validación de stock ocurre aquí  
→ [reporting_pipeline.md](./reporting_pipeline.md) — Reportes leen movimientos acumulados  

## ¿Qué sigue?

Los cambios de inventario quedan registrados en StockMovement para auditoría. El siguiente paso es [invoice_pipeline.md](./invoice_pipeline.md) donde se factura la venta.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [payment_pipeline.md](./payment_pipeline.md)
