---
id: architecture-pricing-pipeline
type: Domain
status: active
owner: operator
last_review: 2026-06-29
tags: [architecture, pricing, taxes, order-economics]
---

# Pricing Pipeline

## ¿Qué es?

El Pricing Pipeline es el proceso mediante el cual se calcula la estructura económica de una orden: subtotal (suma de líneas), impuesto (sobre base), total final.

Estos valores se calculan **una sola vez** durante la creación de la orden y se persisten como campos inmutables. No son dinámicos ni se recalculan.

## ¿Por qué existe?

Las órdenes son transacciones históricas. El precio y el impuesto vistos por el cliente en el momento de compra deben permanecer congelados para:
- Auditoría contable (qué cobró, qué impuesto se pagó)
- Reportes financieros sin ambigüedad
- Reconciliación con pagos y facturación SUNAT
- Prevención de discrepancias si los precios de producto cambian

## Flujo Conceptual

```
OrderItem creado con: quantity, price_at_order
    ↓
Para cada item: subtotal_item = quantity × price_at_order
    ↓
Sumar: subtotal_orden = Σ(subtotal_item)
    ↓
Leer tasa de impuesto (Organization.TaxConfiguration)
    ↓
Calcular: tax_amount = subtotal × (rate / 100)
    ↓
Aplicar redondeo (quantize a 2 decimales)
    ↓
Calcular: total_amount = subtotal + tax_amount
    ↓
Persistir en Order: subtotal, tax_amount, total_amount
```

## Componentes Involucrados

| Componente | Responsabilidad |
|---|---|
| Product | Proporciona `price` capturado en el momento |
| OrderService | Orquesta el cálculo, suma y persistencia |
| TaxConfiguration | Determina tasa vigente para organización |
| Decimal (Python) | Aritmética exacta para dinero (no float) |
| Order | Almacena subtotal, tax_amount, total_amount |

## Invariantes Críticas

- **Sin Redondeo en Ítems**: El precio unitario del item no sufre quantize. Solo el impuesto total.
- **Un Cálculo, Una Persistencia**: Se calcula al crear orden y se guarda con `order.save()`. Jamás se recalcula.
- **Tasa Fija**: La tasa de impuesto leída al momento se congela en el monto. Cambios posteriores a TaxConfiguration no afectan órdenes previas.
- **Moneda Única**: Todos los valores se persisten en Decimal con 2 decimales (centavos/céntimos).

## Relaciones

← [sales_pipeline.md](./sales_pipeline.md) — Cálculo ocurre durante creación de orden  
→ [payment_pipeline.md](./payment_pipeline.md) — Total calculado es lo que se cobra  
→ [reporting_pipeline.md](./reporting_pipeline.md) — Reportes financieros leen montos persistidos  

## ¿Qué sigue?

Una vez calculado, el total queda listo para [payment_pipeline.md](./payment_pipeline.md) donde se registra el pago.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [inventory_pipeline.md](./inventory_pipeline.md)
