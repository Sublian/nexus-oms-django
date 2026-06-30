---
id: architecture-sales-pipeline
type: Domain
status: active
owner: operator
last_review: 2026-06-29
tags: [architecture, sales, order-pipeline]
---

# Sales Pipeline

## ¿Qué es?

El Sales Pipeline es el flujo operacional que transforma una solicitud de orden (con cliente y ítems) en una orden persistida con precios, impuestos y totales calculados, lista para procesamiento subsiguiente (pagos, facturación, entregas).

Inicia cuando un cliente solicita productos y termina cuando la orden alcanza estado PENDING con montos confirmados en la base de datos.

## ¿Por qué existe?

Las órdenes son la unidad de negocio central del OMS. Este pipeline garantiza que:
- Toda orden tiene precios consistentes capturados en el momento de la venta
- Los totales se calculan una sola vez y se persisten (no dinámicos)
- El stock se ajusta automáticamente cuando la orden se crea
- Las órdenes son transaccionales (todo sucede o nada)

## Flujo Conceptual

```
Cliente solicita orden
    ↓
Validación: ¿stock disponible?
    ↓
Creación atómica:
  - Order (PENDING, con subtotal/impuesto/total)
  - OrderItems (cantidad × precio_en_momento_de_venta)
    ↓
Signal: adjust_stock_on_sale
  - Reduce inventario
  - Registra StockMovement (Kárdex)
    ↓
Generación asíncrona: PDF de orden
    ↓
Orden lista para siguiente etapa (pago, facturación)
```

## Componentes Involucrados

| Componente | Responsabilidad |
|---|---|
| OrderService | Orquesta validación, cálculo de montos, creación atómica |
| Order, OrderItem | Persistencia de orden y líneas de venta |
| TaxConfiguration | Determina tasa de impuesto por organización |
| Stock | Inventario disponible verificado antes de crear |
| Signal (adjust_stock_on_sale) | Descuento reactivo de stock cuando se crea item |
| StockMovement | Auditoría (Kárdex) de cada movimiento |
| PDF Task | Generación asíncrona del comprobante |

## Invariantes Críticas

- **Atomicidad**: Si validación falla, Order no se crea. Si creación falla, signal no se dispara.
- **Precios Capturados**: El precio se congela en `price_at_order` al momento de crear item. Cambios posteriores al producto no afectan.
- **Impuesto Único**: Se calcula una sola vez (al crear orden) usando tasa vigente; no se recalcula.
- **Stock Consistente**: Descuento ocurre exactamente una vez por item, mediante signal, bajo lock DB.

## Relaciones

← [pricing_pipeline.md](./pricing_pipeline.md) — Cálculo de totales e impuestos ocurre aquí  
← [inventory_pipeline.md](./inventory_pipeline.md) — Ajuste de stock es una consecuencia  
→ [payment_pipeline.md](./payment_pipeline.md) — Orden de venta espera pago  
→ [invoice_pipeline.md](./invoice_pipeline.md) — Post-pago, orden se factura  

## ¿Qué sigue?

Una vez creada, la orden entra en [payment_pipeline.md](./payment_pipeline.md) donde el cliente registra su medio de pago.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [pricing_pipeline.md](./pricing_pipeline.md)
