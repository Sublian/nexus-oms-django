---
id: architecture-reporting-pipeline
type: Domain
status: active
owner: operator
last_review: 2026-06-29
tags: [architecture, reporting, analytics, celery-beat]
---

# Reporting Pipeline

## ¿Qué es?

El Reporting Pipeline es el proceso automático de consolidación de datos de órdenes, pagos, devoluciones e inventario en reportes ejecutivos (ventas diarias, márgenes netos, movimientos de stock).

Reportes se generan automáticamente en horarios fijos (weekly, daily) y se almacenan como registros persistentes para consulta y auditoría.

## ¿Por qué existe?

Los reportes responden preguntas de negocio críticas:
- ¿Cuánto vendí esta semana?
- ¿Cuál fue mi margen neto?
- ¿Qué productos se movieron?
- ¿Cuál es mi posición de efectivo?

Automatizarlos evita cálculos manuales y errores. Persistirlos permite histórico y auditoría.

## Flujo Conceptual

```
Celery Beat Scheduler
    ↓
Triggers (diario a 06:00 UTC):
  sync_daily_exchange_rate()
    ↓
    Consulta tipo de cambio a APIMigo
    Persiste ExchangeRate para hoy
    ↓
Triggers (lunes 00:00 UTC):
  trigger_periodic_reports()
    ↓
    Itera todas las organizaciones (all_objects, sin filtro tenant)
    ↓
    Para cada org:
      generate_sales_report_task.delay(org_id)
        ↓
        Calcula métricas:
          - Revenue (suma de pagos recibidos)
          - Net Profit (revenue - COGS - fees - refunds)
          - Margin % (net_profit / revenue × 100)
          - Order count
          ↓
        Persiste SalesReport con JSON de datos
        ↓
        Notifica admin por email/telegram/whatsapp
```

## Componentes Involucrados

| Componente | Responsabilidad |
|---|---|
| Celery Beat | Scheduler que dispara tasks a horarios fijos |
| SalesReport | Modelo que almacena métricas consolidadas |
| Payment | Fuente de ingresos |
| OrderReturn | Fuente de devoluciones (reduce margen) |
| OrderItem | Fuente de COGS (costo de mercancía vendida) |
| PurchaseOrderItem | Determina último costo de producto |
| ExchangeRate | Tipo de cambio diario para conversiones |
| NotificationService | Envía reportes a stakeholders |

## Invariantes Críticas

- **Consolidación Punto en Tiempo**: Reporte captura métricas entre start_date y end_date. Inmutable.
- **COGS Reconstructido**: Se consulta última OC recibida para cada producto vendido. Si no existe, asume margen 50%.
- **Revenue de Pagos**: No de órdenes. Solo Payment.amount es dinero real recibido.
- **Devoluciones Deducen**: OrderReturn.refund_amount se resta de revenue.
- **Organización Scoped**: Cada org tiene sus reportes independientes (tenant isolation).

## Relaciones

← [sales_pipeline.md](./sales_pipeline.md) — Órdenes son fuente de datos  
← [payment_pipeline.md](./payment_pipeline.md) — Pagos son fuente de ingresos  
← [inventory_pipeline.md](./inventory_pipeline.md) — COGS y movimientos provienen de aquí  
→ [tenant_flow.md](./tenant_flow.md) — Reportes se aíslan por tenant  

## ¿Qué sigue?

Reportes generados quedan almacenados en SalesReport para consulta. El acceso se realiza a través de dashboards (web views) o APIs.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [tenant_flow.md](./tenant_flow.md)
