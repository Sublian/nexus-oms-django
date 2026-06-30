---
id: domain-inventory
type: Entity
status: active
owner: operator
last_review: 2026-06-29
tags: [domain, inventory, stock, kardex, audit-trail]
---

# Inventory

## ¿Qué es?

El Inventario es el registro de existencias de productos en almacenes, con auditoría completa de cada movimiento (entrada, salida, devolución).

Consta de:
- **Stock**: Cantidad disponible de un producto en un almacén
- **StockMovement (Kárdex)**: Auditoría inmutable de cada cambio, tipo de movimiento, motivo

## ¿Por qué existe?

El inventario es crítico para operaciones:
- Evita sobreventa (validar stock antes de vender)
- Registra auditoría (quién, cuándo, por qué cambió)
- Soporta reportes (rotación, disponibilidad, niveles)
- Permite devoluciones y compras (ajustes bidireccionales)

## Estructura

### Stock
- `product` — Referencia al producto
- `warehouse` — Referencia al almacén físico
- `quantity` — Unidades disponibles (puede ser negativo como excepción)

### StockMovement (Kárdex)
- `stock` — Referencia al registro de stock
- `quantity` — Unidades movidas
- `movement_type` — INPUT (compra), OUTPUT (venta), RETURN (devolución)
- `reason` — Descripción legible ("Venta: Pedido #123", "Compra: OC #45", "Devolución: Ticket #67")
- `order` — Referencia a Order (si viene de venta)
- `created_at` — Timestamp auditoría

## Flujo de Movimientos

### Venta (OUTPUT)
Cuando se crea OrderItem:
1. Valida: `Stock.quantity >= OrderItem.quantity`?
2. Si NO: rechaza, transacción aborta
3. Si SÍ: crea item, signal descuenta stock, registra OUTPUT

### Compra (INPUT)
Cuando PurchaseOrder cambia a RECEIVED:
1. Para cada item de PO:
2. Obtiene (o crea) Stock para product+warehouse
3. Incrementa quantity
4. Registra INPUT

### Devolución (RETURN)
Cuando se registra OrderReturn con `reentered_to_stock=True`:
1. Incrementa Stock.quantity del producto
2. Registra RETURN

## Invariantes Críticas

- **Kárdex Inmutable**: StockMovement nunca se modifica, solo se crea. Es auditoría legal.
- **Validación Previa**: No se usa "replenish later". Stock se valida antes de ordenar venta.
- **Lock en Cambios**: select_for_update() previene condiciones de carrera entre workers.
- **Permitir Negativos**: BD permite quantity < 0 (no hay CHECK constraint). Esto es intencional: permite registrar devoluciones sin fallar, pero debe evitarse.
- **Cantidad Positiva en Movimientos**: StockMovement.quantity siempre es positivo. El tipo (INPUT/OUTPUT) determina dirección.

## Relaciones

→ [orders.md](./orders.md) — Cada venta descuenta stock
→ [payments.md](./payments.md) — Devoluciones de pagos re-ingresan stock

## Niveles de Alerta (No Implementado Aún)

- Stock bajo (< 10 unidades): notificar reabastecimiento
- Stock negativo: alertar, requiere ajuste manual

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [payments.md](./payments.md)
