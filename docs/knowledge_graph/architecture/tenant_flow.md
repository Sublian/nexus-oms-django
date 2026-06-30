---
id: architecture-tenant-flow
type: Domain
status: active
owner: operator
last_review: 2026-06-29
tags: [architecture, multi-tenancy, isolation, context]
---

# Tenant Flow

## ¿Qué es?

El Tenant Flow es el mecanismo de propagación del contexto organizacional (tenant) a través de todas las capas de la aplicación: HTTP requests, web views, API endpoints, Celery tasks, signals, y queries a base de datos.

Garantiza que cada operación ocurre en el contexto correcto sin filtraciones de datos cross-tenant.

## ¿Por qué existe?

SaaS multi-tenant requiere aislación estricta:
- Cada organización ve solo sus datos
- No hay hard-coded organization_id en código
- No hay excepciones o rutas especiales por tenant
- Contexto se propaga automáticamente

## Flujo Conceptual

```
HTTP Request (API o Web)
    ↓
Middleware TenantMiddleware:
  Si API request:
    → Extrae organization_id de JWT claims
  Si Web request:
    → Extrae organization_slug de URL path
    → Resuelve a Organization por slug
    ↓
    set_current_organization(organization_id) en thread-local
    ↓
View recibe request con context
    ↓
ORM Queries (todas las herencias de TenantModel):
  TenantManager.get_queryset()
    ↓
    Automáticamente filtra: filter(organization_id=thread_local_org)
    ↓
    Previene selects sin filtro (get_or_create usa .objects que es TenantManager)

Async Tasks (Celery):
  Opción 1: Sin @tenant_task decorator
    Recibe entry_id
    ↓
    Consulta con all_objects (bypassea filtro)
    ↓
    Extrae organization_id del modelo
    ↓
    Usa manualmente donde necesario
    ↓
  Opción 2: Con @tenant_task decorator
    Especifica organization_id como parámetro
    ↓
    Decorator extrae org_id, calls set_current_organization()
    ↓
    Task body usa ORM normal (filtrado automáticamente)

Signals (post_save, etc.):
  adjust_stock_on_sale(OrderItem)
    ↓
    OrderItem hereda de TenantModel
    ↓
    Accede a organization_id del instance
    ↓
    Queries en signal usan .objects (TenantManager, filtrado)

API Response:
  ↓
  Middleware limpia thread-local antes de retornar
  ↓
  clear_current_organization()
```

## Componentes Involucrados

| Componente | Responsabilidad |
|---|---|
| TenantModel (abstracto) | Base class: agrega organization FK a todos los modelos |
| TenantManager | Manager custom que auto-filtra queries |
| Thread-local context | `multitenancy/context.py`: almacena org_id por request |
| TenantMiddleware | Middleware que asigna context en entrada/salida |
| JWT claims | API: incluye organization_id en token |
| URL routing | Web: incluye org_slug en path (`/dashboard/<org_slug>/`) |
| @tenant_task | Decorator que propaga context a Celery tasks |
| all_objects | Manager sin filtro, para queries cross-tenant (admin, reporting) |

## Invariantes Críticas

- **Automático = Seguro**: TenantManager filtra automáticamente. Código no necesita acordarse.
- **No Bypasseo Accidental**: `.objects.all()` siempre es filtrado. Solo `.all_objects` bypassea.
- **Context por Request**: Thread-local se crea en entrada, limpia en salida. Evita contaminación entre requests.
- **Celery sin Garantía**: Tasks que usan @shared_task (no @tenant_task) deben manejar context manualmente.
- **Signals Heredan**: Si Signal crea/modifica modelo, hereda organization_id del trigger automáticamente.

## Relaciones

→ [sales_pipeline.md](./sales_pipeline.md) — Órdenes se crean con tenant context  
→ [inventory_pipeline.md](./inventory_pipeline.md) — Stock se aísla por tenant  
→ [invoice_pipeline.md](./invoice_pipeline.md) — Facturas son per-tenant  
→ [reporting_pipeline.md](./reporting_pipeline.md) — Reportes consolidan dentro de tenant  

## ¿Qué sigue?

La aislación de tenant es transversal: sustenta todos los pipelines anteriores. Sin ella, las operaciones contaminarían datos cross-tenant.

---

**Estado**: ACTIVE  
**Última actualización**: 2026-06-29  
**Responsable**: Operator  
**Siguiente nodo recomendado**: [architecture/root.md](./root.md) para visión general
