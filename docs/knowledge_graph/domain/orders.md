---
id: domain-orders
type: Entity
status: active
owner: operator
last_review: 2026-06-29
tags: [domain, orders, fsm, state-machine]
---

# Orders

## ¿Qué es?

Una Orden (Order) es el registro de una transacción de venta: qué cliente compró qué productos, en qué cantidad, a qué precio, generando qué monto total y con qué estado de cumplimiento.

Una orden contiene:
- Identificación del cliente (nombre, email)
- Ítems de venta (producto, cantidad, precio capturado)
- Montos calculados (subtotal, impuesto, total)
- Estado de máquina de estados (FSM): DRAFT → PENDING → PAID → SHIPPED → DELIVERED
- Ramificaciones: CANCELLED, REFUNDED

## ¿Por qué existe?

La orden es la entidad central del OMS. Vincula comercio, inventario, finanzas y logística:
- Comercio: ¿Qué se vendió?
- Inventario: ¿Qué stock se descuenta?
- Finanzas: ¿Cuál es el ingreso?
- Logística: ¿Dónde se entrega?
- Cumplimiento: ¿Qué estado tiene?

## Estructura

### Campos Comerciales
- `customer_name`, `customer_email` — Identidad del comprador
- `client` — Referencia a cliente (opcional, para B2B recurrente)
- `delivery_type` — PICKUP o DELIVERY

### Montos (Congelados)
- `subtotal` — Suma de líneas (quantity × price_at_order)
- `tax_amount` — Impuesto sobre subtotal (tasa fija por org)
- `total_amount` — subtotal + tax_amount

### Ítems Relacionados
- `OrderItem` (1:N) — Cada línea de venta con producto, cantidad, precio_histórico

### Ciclo de Vida
- `status` — Estado FSM actual
- `workflow_processed` — Flag: ¿post-pago ejecutado?
- `workflow_status` — Subestado del workflow (pending|processing|completed|failed)

### Facturación
- `invoice_status` — Estado con SUNAT (pending|queued|processing|submitted|accepted|rejected)
- `invoice_external_id` — Serie-número asignado por Nubefact
- `invoice_hash` — CDR recibido de Nubefact
- `invoice_attempts` — Contador de intentos de emisión
- `invoice_last_error` — Último error de facturación

### Documentos
- `pdf_report` — Archivo PDF del comprobante
- `nota` — Campo auditoria: cambios posteriores (incrementos/decrementos/borrados)

## Invariantes Críticas

- **Precios Congelados**: `price_at_order` es inmutable. Cambios al producto no afectan órdenes pasadas.
- **Montos Calculados Una Sola Vez**: Se calculan en creación, nunca se recalculan. Garantiza auditoría.
- **FSM Estricto**: Solo transiciones declaradas son válidas. No se puede ir directo de PENDING a DELIVERED.
- **OneToOne Payment**: Máximo un Payment por Order.
- **OneToOne InvoiceSyncQueue**: Máximo una entrada de sincronización por Order.

## Relaciones

- ← [inventory.md](./inventory.md) — Cada item de orden descuenta stock
- ← [payments.md](./payments.md) — Orden espera pago para avanzar
- → [invoicing.md](./invoicing.md) — Post-pago, orden se factura

## Estados FSM

```
DRAFT
  ↓
PENDING ──→ PAID ──→ SHIPPED ──→ DELIVERED
  ↓              ↓
  └─CANCELLED   REFUNDED
```

Cada transición es explícita y validada. No hay saltos.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [inventory.md](./inventory.md)
